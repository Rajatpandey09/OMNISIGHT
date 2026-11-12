/* OmniSight frontend — complete implementation */
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
const categoryIcons = {
  horizontal_overflow: "↔",
  offscreen_button: "⊠",
  broken_image: "⊡",
  console_error: "⚠",
  network_failure: "✗",
  hidden_control: "◌",
  overlapping_text: "⧉",
  low_contrast: "◑",
  other: "◇",
};
let data={scans:[],issues:[],targets:[],dashboard:null}, currentReview=null, currentDetailScanId=null, toastTimer=null, loadGeneration=0, currentAiFindingIndex=null, currentPage="overview";

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
function setState(el,kind,title,message){if(!el)return;el.hidden=false;el.className=`state-panel state-${kind}`;el.innerHTML=`<span class="state-symbol">${kind==="loading"?"…":kind==="error"?"!":kind==="empty"?"—":"i"}</span><div><b>${esc(title)}</b><p>${esc(message)}</p></div>${kind==="error"?'<button class="text-link retry-button">Try again →</button>':""}`}
function clearState(el){if(!el)return;el.hidden=true;el.innerHTML=""}
function setModeUI() {
  const footerMode = $("#footerMode");
  const scanModeFoot = $("#scanModeFoot");
  if (footerMode) footerMode.textContent = "LIVE API";
  if (scanModeFoot) scanModeFoot.textContent = `API: ${window.OmniSightAPI.baseUrl}`;
}

function renderMetrics() {
  const d = data.dashboard || {};
  const countVerified = data.issues.filter(i => normalizeState(i.state||i.verification_state||i.status) === "verified").length;
  const countAttention = data.issues.filter(i => normalizeState(i.state||i.verification_state||i.status) !== "verified").length;
  if($("#metricScans")) $("#metricScans").textContent = val(d.total_scans, data.scans.length);
  if($("#metricIssues")) $("#metricIssues").textContent = val(d.issues_found, data.issues.length);
  if($("#metricVerified")) $("#metricVerified").textContent = val(d.verified_resolved, countVerified);
  if($("#metricAttention")) $("#metricAttention").textContent = val(d.needs_attention, countAttention);
  if($("#navIssueCount")) $("#navIssueCount").textContent = data.issues.length;
}

function val(v,fallback){return Number.isFinite(Number(v))&&v!==null?String(v):String(fallback)}
function scanStatus(s){const raw=String(s||"unknown").toLowerCase();let cls="neutral";if(raw.includes("complete")||raw==="success")cls="good";else if(raw.includes("partial")||raw.includes("pending")||raw.includes("running")||raw.includes("processing"))cls="warning";else if(raw.includes("fail")||raw.includes("error"))cls="bad";return `<span class="scan-badge scan-${cls}"><i></i>${esc(s||"Unknown")}</span>`}

function renderScans(){
  const rows = data.scans.slice(0,5);
  if($("#recentScans")) {
    $("#recentScans").innerHTML = rows.map(s=>`<tr>
      <td><div class="target-cell"><span class="target-mark">•</span><span><b>${esc(s.target||s.url||"Unnamed target")}</b><small>${esc(s.id||s.scan_id||"Scan")}</small></span></div></td>
      <td>${esc(s.created_at||"—")}</td>
      <td>${esc((s.viewports||[]).join("  ·  ")||s.viewport||"—")}</td>
      <td>${scanStatus(s.status||s.state)}</td>
      <td>${esc(s.issue_count??s.issues_found??"—")}</td>
    </tr>`).join("");
  }
  if($("#historyRows")) {
    $("#historyRows").innerHTML = data.scans.map(s=>`<tr>
      <td><b>${esc(s.id||s.scan_id||"—")}</b></td>
      <td>${esc(s.target||s.url||"—")}</td>
      <td>${esc(s.created_at||"—")}</td>
      <td>${esc((s.viewports||[]).join("  ·  ")||s.viewport||"—")}</td>
      <td>${scanStatus(s.status||s.state)}</td>
      <td>${esc(s.issue_count??s.issues_found??"—")}</td>
      <td>
        <button class="button button-small button-light" data-scandetail="${esc(s.id||s.scan_id||'')}">View →</button>
        <button class="button button-small button-light" data-exportreport="${esc(s.id||s.scan_id||'')}">Export ↓</button>
      </td>
    </tr>`).join("");
  }
  if($("#recentEmpty")) $("#recentEmpty").hidden = rows.length > 0;
  if($("#historyEmpty")) $("#historyEmpty").hidden = data.scans.length > 0;

  // Populate compare dropdowns
  populateCompareSelects();
}

function populateCompareSelects() {
  const a = $("#compareA"), b = $("#compareB");
  if (!a || !b) return;
  const completed = data.scans.filter(s => String(s.status||s.state||"").toLowerCase() === "completed");
  const opts = completed.map(s => `<option value="${esc(s.id||s.scan_id||'')}">
    ${esc((s.target||s.url||"?").slice(0,50))} · ${esc(s.id||s.scan_id||"?")}
  </option>`).join("");
  a.innerHTML = `<option value="">Select scan A</option>${opts}`;
  b.innerHTML = `<option value="">Select scan B (newer)</option>${opts}`;
}

function renderStatus(){
  const counts = Object.keys(stateMeta).map(k=>({key:k,count:data.issues.filter(i=>normalizeState(i.state||i.verification_state||i.status)===k).length}));
  const total = Math.max(data.issues.length,1);
  if($("#statusBreakdown")) $("#statusBreakdown").innerHTML = counts.map(c=>`<div class="status-segment segment-${c.key}" style="width:${c.count/total*100}%"></div>`).join("");
  if($("#statusLegend")) $("#statusLegend").innerHTML = counts.map(c=>`<div><i class="key-dot ${c.key}"></i><span>${stateMeta[c.key].label}</span><b>${c.count}</b></div>`).join("");
  const outstanding = data.issues.filter(i=>normalizeState(i.state||i.verification_state||i.status)!=="verified").sort((a,b)=>severityRank(b.severity)-severityRank(a.severity)).slice(0,3);
  if($("#priorityIssues")) $("#priorityIssues").innerHTML = outstanding.map(i=>`<button class="priority-row" data-review="${esc(i.id||i.issue_id)}">
    <span class="priority-mark">${esc((categoryIcons[i.type||i.issue_type])||"◇")}</span>
    <span class="priority-copy"><b>${esc(i.title||"Untitled issue")}</b><small>${esc(i.viewport||"Viewport unknown")}  ·  ${esc(i.type||i.issue_type||"Issue")}</small></span>
    ${severity(i.severity)}<span class="row-arrow">→</span>
  </button>`).join("");
  if($("#priorityEmpty")) $("#priorityEmpty").hidden = outstanding.length > 0;
}

function severityRank(s){return ({critical:5,high:4,medium:3,low:2,info:1})[String(s||"").toLowerCase()]||0}

function renderIssues() {
  const filter = ($("#statusFilter")||{}).value || "all";
  const q = ($("#globalSearch")||{}).value?.trim().toLowerCase() || "";

  const list = data.issues.filter(i => {
    const st = normalizeState(i.state||i.verification_state||i.status);
    const text = `${i.id||i.issue_id||""} ${i.title||""} ${i.type||i.issue_type||""} ${i.viewport||""} ${i.description||i.summary||""} ${i.category||""}`.toLowerCase();
    return (filter === "all" || st === filter) && (!q || text.includes(q));
  });

  if($("#issueSummary")) $("#issueSummary").textContent = `${list.length} issue${list.length === 1 ? "" : "s"} · backend response`;

  if($("#issueList")) {
    if (!list.length) {
      $("#issueList").innerHTML = "";
    } else {
      // Group by scan_id, preserving insertion order (most-recent first from API)
      const groups = [];
      const groupMap = {};
      for (const i of list) {
        const sid = i.scan_id || "unknown";
        if (!groupMap[sid]) {
          groupMap[sid] = [];
          groups.push(sid);
        }
        groupMap[sid].push(i);
      }

      // Look up target URL for each scan_id from the scans list
      const scanMeta = {};
      for (const s of (data.scans || [])) {
        const sid = s.scan_id || s.id;
        if (sid) scanMeta[sid] = { url: s.url || s.target || "", created_at: s.created_at || "" };
      }

      function issueCard(i) {
        const id = i.id || i.issue_id;
        const view = i.viewport || "Not specified";
        const type = i.type || i.issue_type || "Unclassified";
        const icon = categoryIcons[type] || "◇";
        const hasScreenshot = !!(i.before_screenshot||i.screenshot_url||i.evidence_screenshot);
        return `<article class="issue-row">
          <div class="issue-thumb" aria-hidden="true">
            <div class="thumb-top"><i></i><i></i><i></i></div>
            <div class="thumb-content">
              <span style="font-size:1.5rem;opacity:.6">${icon}</span>
              ${hasScreenshot ? `<img src="${esc(i.before_screenshot||i.screenshot_url||i.evidence_screenshot||'')}" alt="Screenshot" style="width:100%;height:100%;object-fit:cover;position:absolute;inset:0;opacity:.35;border-radius:inherit;" loading="lazy" onerror="this.hidden=true">` : ""}
            </div>
          </div>
          <div class="issue-main">
            <div class="issue-title-line">
              <h3>${esc(i.title || "Untitled issue")}</h3>
              ${severity(i.severity)}
            </div>
            <p>${esc(i.description || i.summary || "No description supplied by the backend.")}</p>
            <div class="issue-meta">
              <span>${esc(id || "ID unavailable")}</span>
              <span>${esc(type)}</span>
              <span>${esc(view)}</span>
            </div>
            <div class="issue-states">
              ${badge(i.state || i.verification_state || i.status)}
              <span class="evidence-hint">${hasScreenshot ? "Screenshot available" : "No screenshot"}</span>
            </div>
          </div>
          <div class="issue-actions">
            <button class="button button-small button-light" data-review="${esc(id || '')}">Review issue →</button>
          </div>
        </article>`;
      }

      $("#issueList").innerHTML = groups.map(sid => {
        const issues = groupMap[sid];
        const meta = scanMeta[sid] || {};
        const url = meta.url ? `<a href="${esc(meta.url)}" target="_blank" rel="noopener" class="scan-group-url">${esc(meta.url.replace(/^https?:\/\//,'').slice(0,60))}${meta.url.length > 63 ? '…' : ''}</a>` : "";
        const ts = meta.created_at ? `<span class="scan-group-ts">${esc(new Date(meta.created_at).toLocaleString())}</span>` : "";
        const count = `<span class="scan-group-count">${issues.length} issue${issues.length === 1 ? "" : "s"}</span>`;
        return `
          <div class="scan-group">
            <div class="scan-group-header">
              <div class="scan-group-left">
                <span class="scan-group-icon">⊡</span>
                <div>
                  <div class="scan-group-title">${esc(sid)}</div>
                  <div class="scan-group-sub">${url}${ts}</div>
                </div>
              </div>
              <div class="scan-group-right">${count}</div>
            </div>
            <div class="scan-group-body">
              ${issues.map(issueCard).join("")}
            </div>
          </div>`;
      }).join("");
    }
  }

  const state = $("#issuesState");
  if(state) {
    state.hidden = list.length > 0;
    if (!list.length) setState(state, "empty", "No matching issues", "Try a different status filter or search term. Run a scan to populate the issue register.");
  }
}

function renderAll(){renderMetrics();renderScans();renderStatus();renderIssues()}

async function loadData() {
  const generation = ++loadGeneration;
  setModeUI();

  const dashState = $("#dashboardState");
  if(dashState) setState(dashState, "loading", "Loading dashboard", "Fetching current data from the backend.");
  const metricGrid = $("#metricGrid");
  if(metricGrid) metricGrid.classList.add("is-loading");

  try {
    const results = await Promise.allSettled([
      window.OmniSightAPI.dashboard(),
      window.OmniSightAPI.scans(),
      window.OmniSightAPI.issues(),
      window.OmniSightAPI.targets()
    ]);

    if (generation !== loadGeneration) return;

    const getResult = (index, fallback) =>
      results[index].status === "fulfilled" ? results[index].value : fallback;

    data = {
      dashboard: getResult(0, {}),
      scans: normalizeArray(getResult(1, [])),
      issues: normalizeArray(getResult(2, [])),
      targets: normalizeTargets(getResult(3, []))
    };

    renderAll();
    fillTargets();
    if(dashState) clearState(dashState);
    clearState($("#issuesState"));
    clearState($("#historyState"));

    if (!data.scans.length && !data.issues.length) {
      if(dashState) setState(dashState, "empty", "No data yet", "No scans have been run yet. Use 'New scan' to get started.");
    }
  } catch (error) {
    if (generation !== loadGeneration) return;
    data = { dashboard: null, scans: [], issues: [], targets: [] };
    renderAll();
    fillTargets();
    if(dashState) setState(dashState, "error", "Backend unavailable", error.message);
    const issState = $("#issuesState");
    if(issState) setState(issState, "empty", "No issues available", "Issues will appear when the backend returns them.");
    const histState = $("#historyState");
    if(histState) setState(histState, "empty", "No scan history available", "Scan history will appear when the backend returns it.");
  } finally {
    if(metricGrid) metricGrid.classList.remove("is-loading");
  }
}

function normalizeArray(v){return Array.isArray(v)?v:Array.isArray(v?.items)?v.items:Array.isArray(v?.results)?v.results:[]}

function normalizeTargets(v) {
  return normalizeArray(v).map(t => ({
    id: t.id ?? t.target_id ?? t.url ?? "",
    name: t.name ?? t.label ?? t.url ?? String(t.id),
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
    select.add(new Option("No pre-configured targets — enter a URL below", ""));
    return;
  }

  targets.forEach(target => {
    const url = target.url || "";
    const option = new Option(target.name || url || "Unnamed", url);
    option.dataset.url = url;
    select.add(option);
  });

  if ([...select.options].some(o => o.value === previousValue)) select.value = previousValue;
  if($("#targetHelp")) $("#targetHelp").textContent = "Pre-configured targets loaded. Or enter any public URL below.";
}

function navigate(page){
  const pages = ["overview","scan","issues","history","review","scandetail"];
  if(!pages.includes(page)) return;
  currentPage = page;
  $$(".page").forEach(p => p.classList.toggle("active", p.id === "page-" + page));
  $$(".nav-link").forEach(n => n.classList.toggle("active", n.dataset.page === page));
  const breadcrumbs = {overview:"Overview",scan:"New scan",issues:"Issues",history:"Scan history",review:"Fix review",scandetail:"Scan detail"};
  const bc = $("#breadcrumb");
  if(bc) bc.textContent = breadcrumbs[page] || page;
  const sidebar = $("#sidebar");
  if(sidebar) sidebar.classList.remove("open");
  if(page === "issues") renderIssues();
  if(page === "review" && currentReview) window.scrollTo({top:0,behavior:"auto"});
  // Show/hide export button on review page
  const exportBtn = $("#exportScanBtn");
  if(exportBtn) exportBtn.style.display = (page === "review" && currentReview?.scan_id) ? "inline-flex" : "none";
}

async function handleScan(e) {
  e.preventDefault();
  const desktop = $("#desktopViewport")?.checked;
  const mobile = $("#mobileViewport")?.checked;
  const select = $("#target");
  const option = select?.options[select.selectedIndex];
  const customUrl = ($("#customTargetUrl")?.value || "").trim();
  const url = customUrl || option?.dataset?.url || option?.value;

  if (!desktop && !mobile) { if($("#scanFeedback")) $("#scanFeedback").textContent = "Select at least one viewport."; return; }
  if (!url || !/^https?:\/\//i.test(url)) { if($("#scanFeedback")) $("#scanFeedback").textContent = "Enter a valid HTTP/HTTPS URL (e.g. https://example.com)."; return; }

  const btn = $("#runScanButton");
  if(btn) btn.disabled = true;
  const viewports = [...(desktop ? ["desktop"] : []), ...(mobile ? ["mobile"] : [])];
  if($("#scanFeedback")) $("#scanFeedback").textContent = `Starting scan on ${url}…`;

  try {
    const result = await window.OmniSightAPI.createScan({ url, viewports });
    const scanId = result.scan_id || result.id;
    if (!scanId) throw new Error("The backend did not return a scan ID.");

    if($("#scanFeedback")) $("#scanFeedback").innerHTML = `<b>Scan ${scanId} accepted.</b> Playwright is running — please wait…`;

    // Poll for completion
    let latest = result;
    for (let attempt = 0; attempt < 120; attempt++) {
      await new Promise(r => setTimeout(r, 1500));
      latest = await window.OmniSightAPI.scan(scanId);
      const state = String(latest.status || latest.state || "").toLowerCase();
      if($("#scanFeedback")) {
        const dots = ".".repeat((attempt % 3) + 1);
        $("#scanFeedback").textContent = `Scanning${dots} (${state})`;
      }
      if (state === "completed") break;
      if (state === "failed" || state === "error") throw new Error(latest.error || "Browser scan failed.");
    }

    const finalState = String(latest.status || latest.state || "").toLowerCase();
    if (finalState !== "completed") throw new Error("Scan timed out. Check Scan history for the result.");

    const viewportCount = (latest.results || []).length;
    const issueCount = latest.issue_count || 0;
    if($("#scanFeedback")) {
      $("#scanFeedback").innerHTML = `<b>✓ Scan complete:</b> ${esc(scanId)} · ${viewportCount} viewport${viewportCount!==1?"s":""} · ${issueCount} issue${issueCount!==1?"s":""} detected. <button class="text-link" data-scandetail="${esc(scanId)}">View screenshots →</button>`;
    }
    await loadData();
    toast("Scan completed. Screenshots and issues are ready.");
    // Navigate to issues tab if issues were found
    if (issueCount > 0) setTimeout(() => navigate("issues"), 1200);
  } catch (error) {
    console.error("Scan failed:", error);
    if($("#scanFeedback")) $("#scanFeedback").textContent = `Scan failed: ${error.message}`;
    toast("Scan failed: " + error.message);
  } finally {
    if(btn) { btn.disabled = false; btn.innerHTML = 'Run scan <span>↗</span>'; }
  }
}

function imagePanel(url, label){
  if(url) return `<figure class="screenshot-frame">
    <img src="${esc(url)}" alt="${esc(label)} screenshot" loading="lazy"
      onerror="this.hidden=true;this.nextElementSibling.hidden=false">
    <div class="image-unavailable" hidden>Screenshot could not be loaded.</div>
    <figcaption>${esc(label)}</figcaption>
  </figure>`;
  return `<div class="screenshot-placeholder">
    <div class="placeholder-browser"><i></i><i></i><i></i></div>
    <div class="placeholder-lines"><span></span><span></span><span></span></div>
    <div class="placeholder-message">No screenshot supplied by the backend</div>
    <small>${esc(label)}</small>
  </div>`;
}

function openReview(id, preservePage=false){
  const issue = data.issues.find(i => String(i.id||i.issue_id) === String(id));
  if (!issue) { toast("Issue details not found in current data."); return; }
  currentReview = issue;
  if(!preservePage) navigate("review");
  const state = normalizeState(issue.state||issue.verification_state||issue.status);
  const before = issue.before_screenshot||issue.screenshot_url||issue.evidence_screenshot||"";
  const after = issue.after_screenshot||issue.verification_screenshot||"";
  const icon = categoryIcons[issue.type||issue.issue_type] || "◇";

  $("#reviewContent").innerHTML = `
    <section class="surface review-main">
      <div class="review-title">
        <div>
          <span class="eyebrow">${esc(issue.id||issue.issue_id||"ISSUE")}  ·  ${esc(issue.type||issue.issue_type||"Finding")}</span>
          <h2>${icon} ${esc(issue.title||"Untitled issue")}</h2>
        </div>
        ${badge(state)}
      </div>
      <p class="review-description">${esc(issue.description||issue.summary||"No description provided.")}</p>
      ${issue.ai_suggested_fix ? `<div class="review-section"><span class="eyebrow">VISION MODEL SUGGESTION</span><p class="review-description">${esc(issue.ai_suggested_fix)}</p><p class="image-caption">Advisory text only.</p></div>` : ""}
      <div class="review-meta">
        ${severity(issue.severity)}
        <span class="meta-pill">${esc(issue.viewport||"Viewport unknown")}</span>
        <span class="meta-pill">Scan: ${esc(issue.scan_id||"Not supplied")}</span>
        <span class="meta-pill">Source: ${esc(issue.source||"playwright")}</span>
        ${issue.target_url ? `<span class="meta-pill"><a href="${esc(issue.target_url)}" target="_blank" rel="noopener">${esc(issue.target_url.slice(0,40))}…</a></span>` : ""}
      </div>
      <div class="review-section">
        <div class="section-heading">
          <div><span class="eyebrow">VISUAL EVIDENCE</span><h2>Screenshots</h2></div>
          <span class="mini-label">Real backend images when available</span>
        </div>
        <div class="comparison-grid">
          ${imagePanel(before,"Captured (before fix)")}
          ${imagePanel(after,"After verification")}
        </div>
        <p class="image-caption">Missing screenshots shown as placeholders, never replaced with invented evidence.</p>
      </div>
      ${issue.suggested_css||issue.proposed_css ? `<div class="review-section"><span class="eyebrow">PROPOSED CHANGE</span><h2>Suggested CSS</h2><pre class="css-proposal">${esc(issue.suggested_css||issue.proposed_css)}</pre><p class="image-caption">Review this change before approval. This UI does not apply CSS to the target site.</p></div>` : ""}
      <div class="review-section">
        <span class="eyebrow">VERIFICATION OUTCOME</span>
        <h2>Current result</h2>
        <div class="verification-box state-${state}">
          <span class="verification-icon">${state==="verified"?"✓":state==="failed"?"!":state==="inconclusive"?"?":"•"}</span>
          <div>
            <b>${esc(issue.verification_outcome||stateMeta[state].label)}</b>
            <p>${esc(issue.evidence||issue.verification_details||"No additional verification details supplied.")}</p>
          </div>
        </div>
      </div>
      <div id="reviewState" class="state-panel" hidden></div>
      <div class="review-actions" id="reviewActions"></div>
    </section>
    <aside class="surface review-aside">
      <span class="eyebrow">REVIEW CHECKLIST</span>
      <h2>Before you approve</h2>
      <ul class="checklist">
        <li><span>01</span><div><b>Confirm the issue</b><small>Check the viewport and supporting evidence.</small></div></li>
        <li><span>02</span><div><b>Inspect the CSS</b><small>Make sure the proposal is scoped and safe.</small></div></li>
        <li><span>03</span><div><b>Verify separately</b><small>Approval is not the same as a successful fix.</small></div></li>
      </ul>
      <div class="human-note"><b>Human approval required</b><p>Only a successful follow-up verification may move an issue to Verified.</p></div>
    </aside>`;

  const actions = $("#reviewActions");
  if(state === "proposed") {
    actions.innerHTML = `<button class="button button-dark" id="runIsolatedHeal">Test AI fix in isolated browser →</button><button class="button button-light" id="approveAndVerify">Approve &amp; verify proposed CSS</button><button class="button button-light" id="rejectFix">Reject proposal</button><button class="text-link" id="runVisionAnalysis">Re-run VLM analysis</button>`;
  } else if (state === "applied") {
    actions.innerHTML = `<button class="button button-dark" id="verifyFix">Run verification →</button>`;
  } else {
    actions.innerHTML = `<button class="button button-dark" id="runVisionAnalysis">Analyze screenshots with Vision AI →</button><span class="action-note">AI proposals are tested in an isolated browser; the original site is not modified.</span>`;
  }

  // Show export button
  const exportBtn = $("#exportScanBtn");
  if(exportBtn && issue.scan_id) {
    exportBtn.style.display = "inline-flex";
    exportBtn.dataset.scanid = issue.scan_id;
  }
}

async function openScanDetail(scanId) {
  currentDetailScanId = scanId;
  navigate("scandetail");
  const content = $("#scanDetailContent");
  if (!content) return;
  setState(content, "loading", "Loading scan", "Fetching scan data…");

  try {
    const scan = await window.OmniSightAPI.scan(scanId);
    const apiOrigin = window.OmniSightAPI.baseUrl.replace(/\/api\/?$/, "");
    const results = scan.results || [];
    const issuesForScan = data.issues.filter(i => i.scan_id === scanId);

    content.innerHTML = `
      <div class="surface" style="padding:1.5rem;margin-bottom:1.5rem">
        <div class="review-title">
          <div>
            <span class="eyebrow">SCAN METADATA</span>
            <h2>${esc(scan.url||scan.target||"Unknown URL")}</h2>
          </div>
          ${scanStatus(scan.status||scan.state)}
        </div>
        <div class="review-meta" style="margin-top:1rem">
          <span class="meta-pill">ID: ${esc(scan.scan_id||scan.id||"?")}</span>
          <span class="meta-pill">Started: ${esc(scan.created_at||"?")}</span>
          <span class="meta-pill">Completed: ${esc(scan.completed_at||"?")}</span>
          <span class="meta-pill">Viewports: ${esc((scan.viewports||[]).join(", ")||"?")}</span>
          <span class="meta-pill">Issues: ${issuesForScan.length}</span>
        </div>
        ${scan.error ? `<div class="notice" style="margin-top:1rem"><span>⚠</span><p>Error: ${esc(scan.error)}</p></div>` : ""}
      </div>
      <div class="dashboard-grid" style="grid-template-columns:repeat(auto-fit,minmax(320px,1fr))">
        ${results.map(r => {
          const shotUrl = r.screenshot ? `${apiOrigin}/artifacts/${encodeURIComponent(r.screenshot.split(/[\\/]/).pop())}` : null;
          const m = r.metrics || {};
          const issueCount = issuesForScan.filter(i => i.viewport === r.viewport).length;
          return `<div class="surface" style="padding:1.25rem">
            <span class="eyebrow">${esc(r.viewport?.toUpperCase()||"VIEWPORT")} — ${r.width}×${r.height}</span>
            <h3 style="margin:0.5rem 0">${esc(r.viewport||"?")} screenshot</h3>
            ${shotUrl ? `<img src="${esc(shotUrl)}" alt="${esc(r.viewport)} screenshot" style="width:100%;border-radius:8px;margin-bottom:1rem;border:1px solid var(--border)" loading="lazy" onerror="this.style.display='none'">` : `<div class="screenshot-placeholder" style="height:160px;margin-bottom:1rem"></div>`}
            <div class="issue-meta" style="flex-wrap:wrap;gap:0.5rem">
              <span>Scroll: ${m.scroll_width||"?"}×${m.scroll_height||"?"}</span>
              <span>Overflow: ${m.has_horizontal_overflow ? "⚠ Yes" : "✓ No"}</span>
              <span>Images: ${(m.images||[]).length} (${(m.broken_images||[]).length} broken)</span>
              <span>Buttons: ${(m.buttons||[]).length}</span>
              <span>Console errors: ${(r.console_errors||[]).filter(e=>e.level==="error").length}</span>
              <span>Net failures: ${(r.network_failures||[]).length}</span>
            </div>
            ${issueCount ? `<p style="margin-top:0.75rem"><button class="text-link" data-page="issues">View ${issueCount} issue${issueCount!==1?"s":""} →</button></p>` : `<p style="margin-top:0.75rem;color:var(--accent-green)">✓ No issues detected in this viewport</p>`}
          </div>`;
        }).join("")}
      </div>
      ${issuesForScan.length ? `
      <div class="surface" style="padding:1.5rem;margin-top:1.5rem">
        <span class="eyebrow">DETECTED ISSUES</span>
        <h2 style="margin-bottom:1rem">Issues from this scan</h2>
        <div class="issue-list" style="margin:0">
          ${issuesForScan.map(i => `<article class="issue-row">
            <div class="issue-main">
              <div class="issue-title-line"><h3>${esc(i.title||"Issue")}</h3>${severity(i.severity)}</div>
              <p>${esc(i.description||"")}</p>
              <div class="issue-meta"><span>${esc(i.type||"?")}</span><span>${esc(i.viewport||"?")}</span></div>
            </div>
            <div class="issue-actions">
              <button class="button button-small button-light" data-review="${esc(i.id||i.issue_id||'')}">Review →</button>
            </div>
          </article>`).join("")}
        </div>
      </div>` : ""}`;
  } catch (err) {
    setState(content, "error", "Could not load scan", err.message);
  }
}

async function runCompare() {
  const a = ($("#compareA")||{}).value, b = ($("#compareB")||{}).value;
  if (!a || !b) { toast("Select two scans to compare."); return; }
  if (a === b) { toast("Select two different scans."); return; }
  const btn = $("#runCompareBtn");
  if(btn) { btn.disabled = true; btn.textContent = "Comparing…"; }
  const result = $("#compareResult");
  if(result) { result.hidden = false; result.innerHTML = '<p style="opacity:.6">Loading comparison…</p>'; }
  try {
    const diff = await window.OmniSightAPI.compareScans(a, b);
    const badge = (n, label, cls) => n > 0 ? `<span class="state-badge state-${cls}"><i></i>${n} ${label}</span>` : "";
    result.innerHTML = `
      <div class="compare-scans-grid">
        <div>
          <span class="eyebrow">SCAN A</span>
          <p><b>${esc(diff.scan_a?.url||"?")}</b></p>
          <p>${esc(diff.scan_a?.scan_id||"?")} · ${esc(diff.scan_a?.created_at||"?")} · ${diff.scan_a?.issue_count||0} issues</p>
        </div>
        <div>
          <span class="eyebrow">SCAN B (newer)</span>
          <p><b>${esc(diff.scan_b?.url||"?")}</b></p>
          <p>${esc(diff.scan_b?.scan_id||"?")} · ${esc(diff.scan_b?.created_at||"?")} · ${diff.scan_b?.issue_count||0} issues</p>
        </div>
      </div>
      <div class="compare-summary">
        ${badge(diff.summary?.new, "new", "failed")}
        ${badge(diff.summary?.resolved, "resolved", "verified")}
        ${badge(diff.summary?.recurring, "recurring", "proposed")}
      </div>
      ${diff.new_issues?.length ? `<div class="compare-section"><h3>🔴 New issues (${diff.new_issues.length})</h3><ul>${diff.new_issues.map(i => `<li><b>${esc(i.viewport)}</b> · ${esc(i.type)} ${i.detail ? `· ${esc(i.detail)}` : ""}</li>`).join("")}</ul></div>` : ""}
      ${diff.resolved_issues?.length ? `<div class="compare-section"><h3>✅ Resolved issues (${diff.resolved_issues.length})</h3><ul>${diff.resolved_issues.map(i => `<li><b>${esc(i.viewport)}</b> · ${esc(i.type)} ${i.detail ? `· ${esc(i.detail)}` : ""}</li>`).join("")}</ul></div>` : ""}
      ${diff.recurring_issues?.length ? `<div class="compare-section"><h3>🔄 Recurring issues (${diff.recurring_issues.length})</h3><ul>${diff.recurring_issues.map(i => `<li><b>${esc(i.viewport)}</b> · ${esc(i.type)}</li>`).join("")}</ul></div>` : ""}
      ${!diff.new_issues?.length && !diff.resolved_issues?.length && !diff.recurring_issues?.length ? `<p style="color:var(--accent-green)">✓ No differences between these two scans.</p>` : ""}`;
  } catch(err) {
    if(result) result.innerHTML = `<p style="color:var(--st-failed-text)">Comparison failed: ${esc(err.message)}</p>`;
    toast("Comparison failed: " + err.message);
  } finally {
    if(btn) { btn.disabled = false; btn.textContent = "Compare scans →"; }
  }
}

async function exportReport(scanId) {
  if (!scanId) return toast("No scan ID to export.");
  toast("Preparing export…");
  try {
    const report = await window.OmniSightAPI.exportReport(scanId);
    const json = JSON.stringify(report, null, 2);
    const blob = new Blob([json], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `omnisight-report-${scanId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast(`Report exported: omnisight-report-${scanId}.json`);
  } catch(err) {
    toast("Export failed: " + err.message);
  }
}

async function runVisionAnalysis() {
  if (!currentReview || !currentReview.scan_id) return toast("This issue has no scan ID.");
  navigate("review");
  const scanId = currentReview.scan_id;
  const issueId = currentReview.id || currentReview.issue_id;
  const button = $("#runVisionAnalysis");
  if (button) { button.disabled = true; button.textContent = "Analyzing screenshots…"; }
  try {
    const result = await window.OmniSightAPI.analyzeScan(scanId, false);
    const viewport = currentReview.viewport || "mobile";
    const analysis = (result.analyses || []).find(item => item.viewport === viewport);
    const findings = analysis?.findings || [];
    if (!analysis || analysis.outcome !== "ok" || !findings.length) {
      setState($("#reviewState"), "empty", "Vision analysis completed", (analysis?.error) || (analysis?.outcome) || "No actionable visual finding returned. Check that Ollama is running and the model is pulled.");
      return toast("Vision analysis returned no actionable finding.");
    }
    const preferred = findings.findIndex(item => item.issue_type === (currentReview.type || currentReview.issue_type));
    currentAiFindingIndex = preferred >= 0 ? preferred : 0;
    const finding = findings[currentAiFindingIndex];
    // Build the screenshot URL from the scan results if the issue doesn't already have one
    const apiOriginVlm = window.OmniSightAPI.baseUrl.replace(/\/api\/?$/, "");
    const vlmScanData = await window.OmniSightAPI.scan(scanId).catch(() => null);
    const vlmViewport = (currentReview.viewport || "mobile");
    const vlmResult = (vlmScanData?.results || []).find(r => r.viewport === vlmViewport);
    const vlmShotFile = vlmResult?.screenshot ? String(vlmResult.screenshot).split(/[\\/]/).pop() : "";
    const vlmShotUrl = vlmShotFile ? `${apiOriginVlm}/artifacts/${encodeURIComponent(vlmShotFile)}` : (currentReview.before_screenshot || currentReview.screenshot_url || "");
    Object.assign(currentReview, {
      type: finding.issue_type, issue_type: finding.issue_type,
      title: finding.summary || finding.issue_type.replaceAll("_"," "),
      description: finding.evidence || finding.impact || "Vision model identified a possible visual defect.",
      severity: finding.severity, ai_suggested_fix: finding.suggested_fix || "",
      element: finding.element || "",
      state: finding.suggested_fix ? "proposed" : "detected",
      verification_state: "detected",
      evidence: "VLM confidence: " + Math.round((finding.confidence || 0)*100) + "%. " + (finding.impact || ""),
      aiFindingIndex: currentAiFindingIndex,
      before_screenshot: vlmShotUrl,
      screenshot_url: vlmShotUrl
    });
    const existing = data.issues.find(item => String(item.id||item.issue_id) === String(issueId));
    if (existing) Object.assign(existing, currentReview);
    openReview(issueId, true);
    navigate("review");
    setState($("#reviewState"), "success", "Vision AI analysis completed",
      `${analysis.viewport} · ${finding.issue_type} · ${Math.round((finding.confidence || 0)*100)}% confidence. ${finding.evidence || finding.summary || ""}`);
    toast("Vision findings loaded.");
  } catch (error) {
    const panel = $("#reviewState");
    if (panel) setState(panel, "error", "Vision analysis failed", error.message);
    console.error("Vision analysis failed:", error);
    toast("Vision analysis failed: " + error.message);
  } finally {
    const liveButton = $("#runVisionAnalysis");
    if (liveButton) { liveButton.disabled = false; liveButton.textContent = "Analyze screenshots with Vision AI →"; }
  }
}

async function runIsolatedHealing() {
  if (!currentReview || currentReview.aiFindingIndex === undefined) return toast("Run Vision AI analysis first.");
  const button = $("#runIsolatedHeal");
  if (button) { button.disabled = true; button.textContent = "Testing isolated fix…"; }
  try {
    const result = await window.OmniSightAPI.healScan(currentReview.scan_id, currentReview.aiFindingIndex, currentReview.viewport || "mobile", 2);
    const attempts = (result.attempts || []).map(a => `Attempt ${a.number}: ${a.verdict} — ${a.reason}`).join(" | ") || "No patch attempt produced.";
    if (result.final_css) {
      Object.assign(currentReview, { suggested_css: result.final_css, state: "proposed", aiGeneratedSafePatch: true });
      const id = currentReview.id || currentReview.issue_id;
      const existing = data.issues.find(item => String(item.id||item.issue_id) === String(id));
      if (existing) Object.assign(existing, currentReview);
      openReview(id);
    }
    setState($("#reviewState"), result.status === "fixed" ? "success" : "info",
      "Isolated browser result: " + result.status,
      result.message + " " + attempts + (result.final_css ? " CSS: " + result.final_css : "") + " Original source files were not modified.");
    toast("Isolated self-healing: " + result.status);
  } catch (error) {
    const isTimeout = error.message?.toLowerCase().includes("timed out") || error.message?.toLowerCase().includes("timeout");
    const msg = isTimeout
      ? "Ollama took too long to respond. This usually means the model is under memory pressure. Try: close other apps, run `ollama stop qwen2.5vl:3b` in your terminal to free VRAM, then try again."
      : error.message;
    setState($("#reviewState"), "error", "Self-healing test failed", msg);
    toast("Self-healing test failed.");
  } finally {
    if (button) { button.disabled = false; button.textContent = "Test AI fix in isolated browser →"; }
  }
}

async function approveAndVerifyPatch() {
  if (!currentReview) return;
  const css = currentReview.suggested_css || currentReview.proposed_css || "";
  if (!css.trim()) return toast("No CSS proposal to apply.");
  if (!currentReview.scan_id || !currentReview.target_url) return toast("Original scan or target URL is missing.");
  if (!window.confirm("Approve this CSS proposal and test it in an isolated browser? The original website files will not be modified.")) return;
  const button = $("#approveAndVerify");
  if (button) { button.disabled = true; button.textContent = "Applying in isolated browser…"; }
  try {
    const viewport = currentReview.viewport || "mobile";
    const result = await window.OmniSightAPI.rescanWithPatch({
      url: currentReview.target_url, scan_id: currentReview.scan_id,
      viewports: [viewport], issue_type: currentReview.type || currentReview.issue_type, css_patch: css
    });
    if (!result.rescan_id || !result.scan_data || result.scan_status !== "completed")
      throw new Error("The follow-up scan did not complete; no fix can be verified.");
    const verification = await window.OmniSightAPI.verifyVisionPatch(currentReview.scan_id, {
      rescan_id: result.rescan_id, viewport, issue_type: currentReview.type || currentReview.issue_type, element: currentReview.element || ""
    });
    const state = verification.verification_state === "verified_resolved" ? "verified" : (verification.verification_state === "verification_failed" ? "failed" : "inconclusive");
    const after = (result.scan_data.results || []).find(item => item.viewport === viewport);
    const filename = after?.screenshot ? String(after.screenshot).split(/[\\/]/).pop() : "";
    const apiOrigin = window.OmniSightAPI.baseUrl.replace(/\/api\/?$/, "");

    // Persist the verification outcome to the DB so it survives refresh/restart
    try {
      await window.OmniSightAPI.persistVerification(
        currentReview.scan_id,
        verification.verification_state,
        result.rescan_id,
        currentReview.suggested_css || ""
      );
    } catch(_) { /* non-fatal — UI still updates even if persist fails */ }

    Object.assign(currentReview, {
      state, verification_state: verification.verification_state,
      verification_outcome: verification.verification_state, verification_details: verification.reason,
      before_screenshot: currentReview.before_screenshot || currentReview.screenshot_url || "",
      after_screenshot: filename ? `${apiOrigin}/artifacts/${encodeURIComponent(filename)}` : ""
    });
    const id = currentReview.id || currentReview.issue_id;
    const existing = data.issues.find(item => String(item.id||item.issue_id) === String(id));
    if (existing) Object.assign(existing, currentReview);
    openReview(id);
    setState($("#reviewState"), state === "verified" ? "success" : "info",
      "Follow-up verification: " + verification.verification_state,
      verification.reason + " Model: " + verification.model_verdict + ". Metrics fixed: " + verification.metrics_fixed + ". Source files not modified.");
    toast("Follow-up verification: " + verification.verification_state);
  } catch (error) {
    setState($("#reviewState"), "error", "Patch verification failed", error.message);
    toast("Patch verification failed.");
  } finally {
    if (button) { button.disabled = false; button.textContent = "Approve & verify proposed CSS"; }
  }
}

async function reviewAction(action) {
  if (!currentReview) return;
  const id = currentReview.id || currentReview.issue_id;
  const buttons = $$("#reviewActions button");
  buttons.forEach(b => b.disabled = true);
  try {
    if (action === "approve") await window.OmniSightAPI.approveFix(id);
    else if (action === "reject") await window.OmniSightAPI.rejectFix(id);
    else if (action === "verify") await window.OmniSightAPI.verifyFix(id);
    toast("Backend accepted the request. Reloading data.");
    await loadData();
    openReview(id);
  } catch (error) {
    toast(`Request failed: ${error.message}`);
    buttons.forEach(b => b.disabled = false);
  }
}

// Global click handler
document.addEventListener("click", e => {
  const page = e.target.closest("[data-page]");
  if (page) { e.preventDefault(); navigate(page.dataset.page); return; }

  const review = e.target.closest("[data-review]");
  if (review) { openReview(review.dataset.review); return; }

  const scandetail = e.target.closest("[data-scandetail]");
  if (scandetail) { openScanDetail(scandetail.dataset.scandetail); return; }

  const exportrep = e.target.closest("[data-exportreport]");
  if (exportrep) { exportReport(exportrep.dataset.exportreport); return; }

  if (e.target.closest("#mobileMenu")) {
    const menuButton = $("#mobileMenu"), sidebar = $("#sidebar");
    const isOpen = sidebar.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    return;
  }
  if (e.target.closest("#refreshButton")) { loadData(); return; }
  if (e.target.closest("#themeToggle")) { document.body.classList.toggle("dark"); return; }
  if (e.target.closest("#backToIssues")) { navigate("issues"); return; }
  if (e.target.closest("#backToHistory")) { navigate("history"); return; }
  if (e.target.closest("#runVisionAnalysis")) { e.preventDefault(); e.stopPropagation(); runVisionAnalysis(); return; }
  if (e.target.closest("#runIsolatedHeal")) { e.preventDefault(); e.stopPropagation(); runIsolatedHealing(); return; }
  if (e.target.closest("#approveAndVerify")) { e.preventDefault(); e.stopPropagation(); approveAndVerifyPatch(); return; }
  if (e.target.closest("#approveFix")) { reviewAction("approve"); return; }
  if (e.target.closest("#rejectFix")) { reviewAction("reject"); return; }
  if (e.target.closest("#verifyFix")) { reviewAction("verify"); return; }
  if (e.target.closest(".retry-button")) { loadData(); return; }
  if (e.target.closest("#runCompareBtn")) { runCompare(); return; }
  if (e.target.closest("#exportScanBtn")) {
    const btn = $("#exportScanBtn");
    exportReport(btn?.dataset?.scanid || currentReview?.scan_id);
    return;
  }
  if (e.target.closest("#exportDetailBtn")) {
    exportReport(currentDetailScanId);
    return;
  }
});

const scanForm = $("#scanForm");
if(scanForm) scanForm.addEventListener("submit", handleScan);
const statusFilter = $("#statusFilter");
if(statusFilter) statusFilter.addEventListener("change", renderIssues);
const globalSearch = $("#globalSearch");
if(globalSearch) globalSearch.addEventListener("input", () => {
  if (globalSearch.value.trim()) navigate("issues");
  renderIssues();
});

document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    if(globalSearch) globalSearch.focus();
  }
  if (e.key === "Escape") {
    const sidebar = $("#sidebar"), menuButton = $("#mobileMenu");
    if(sidebar) sidebar.classList.remove("open");
    if(menuButton) {
      menuButton.setAttribute("aria-expanded", "false");
      menuButton.setAttribute("aria-label", "Open navigation");
    }
  }
});

// Add compare styles
const style = document.createElement("style");
style.textContent = `
  .compare-controls{display:flex;flex-wrap:wrap;gap:1rem;align-items:flex-end;margin-bottom:1.5rem}
  .compare-controls select{flex:1;min-width:200px}
  .compare-result{margin-top:1rem;padding:1.25rem;border-radius:var(--radius-md);background:var(--surface-soft);border:1px solid var(--border)}
  .compare-scans-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1rem}
  .compare-summary{display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem}
  .compare-section{margin-bottom:1rem}
  .compare-section h3{font-size:.9rem;font-weight:600;margin-bottom:.5rem}
  .compare-section ul{padding-left:1.5rem;font-size:.875rem;line-height:1.7}
  .compare-surface .field-label{display:block;font-size:.8rem;font-weight:600;color:var(--text-secondary);margin-bottom:.25rem;text-transform:uppercase;letter-spacing:.05em}
  #page-scandetail .issue-row{padding:1rem 1.25rem}
`;
document.head.appendChild(style);

loadData();
})();
