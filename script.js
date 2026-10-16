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
const demoScans=[
{id:"DEMO-014",target:"shop.demo.local",created_at:"Today, 10:42",viewports:["Desktop","Mobile"],status:"completed",issue_count:4},
{id:"DEMO-013",target:"docs.demo.local",created_at:"Yesterday, 16:18",viewports:["Desktop"],status:"completed",issue_count:2},
{id:"DEMO-012",target:"landing.demo.local",created_at:"12 Oct 2026",viewports:["Mobile"],status:"partial",issue_count:3}
];
const demoIssues=[
{id:"OS-101",title:"Primary action overlaps sticky footer",type:"Layout",viewport:"Mobile",severity:"High",description:"The main call-to-action is partly obscured by a fixed footer at 390px viewport width.",state:"proposed",scan_id:"DEMO-014",before_screenshot:"",after_screenshot:"",suggested_css:".checkout-button { position: relative; z-index: 2; margin-bottom: 1rem; }",verification_outcome:"Awaiting approval",evidence:"The demo finding indicates an overlap between the primary action and the sticky footer. Confirm element bounds in the captured evidence before applying a change."},
{id:"OS-102",title:"Hero media exceeds content width",type:"Layout",viewport:"Mobile",severity:"Medium",description:"Hero media extends past the content column and may cause horizontal page overflow.",state:"detected",scan_id:"DEMO-014",before_screenshot:"",after_screenshot:"",suggested_css:"img.hero-media { max-width: 100%; height: auto; object-fit: cover; }",verification_outcome:"Not run",evidence:"The illustrative mobile capture indicates the image extends beyond its parent container."},
{id:"OS-103",title:"Secondary action has weak contrast",type:"Accessibility",viewport:"Desktop",severity:"High",description:"The secondary action may not meet the intended text/background contrast.",state:"proposed",scan_id:"DEMO-013",before_screenshot:"",after_screenshot:"",suggested_css:".button-secondary { color: #263246; background: #f4f6fa; }",verification_outcome:"Awaiting approval",evidence:"Check the actual computed colors and applicable contrast threshold before approving this proposal."},
{id:"OS-104",title:"Product cards use inconsistent corner radius",type:"Visual",viewport:"Desktop",severity:"Low",description:"Card corners use different radius values across the same component group.",state:"applied",scan_id:"DEMO-013",before_screenshot:"",after_screenshot:"",suggested_css:".product-card { border-radius: 12px; }",verification_outcome:"Verification not yet confirmed",evidence:"The demo finding shows inconsistent card radii. The applied change remains unverified until a follow-up scan succeeds."},
{id:"OS-105",title:"Horizontal page scrolling at 390px",type:"Layout",viewport:"Mobile",severity:"High",description:"A child element appears wider than the viewport, creating sideways scrolling.",state:"inconclusive",scan_id:"DEMO-012",before_screenshot:"",after_screenshot:"",suggested_css:"/* Inspect the overflowing child width; avoid hiding overflow globally. */",verification_outcome:"Inconclusive — more evidence required",evidence:"The sample result does not identify the responsible element with sufficient confidence."},
{id:"OS-106",title:"Form submit control is not visible",type:"Visibility",viewport:"Desktop",severity:"Medium",description:"The expected submit control is absent from the available capture.",state:"failed",scan_id:"DEMO-012",before_screenshot:"",after_screenshot:"",suggested_css:".form-submit { display: inline-flex; visibility: visible; }",verification_outcome:"Verification failed",evidence:"The illustrative follow-up did not confirm that the submit control became visible."}
];
let data={scans:[],issues:[],targets:[],dashboard:null}, currentReview=null, toastTimer=null, loadGeneration=0;

const DEMO_STORAGE_KEY = "omnisight.demo.scans.v1";
const DEMO_ISSUES_STORAGE_KEY = "omnisight.demo.issues.v1";

function readSavedDemoIssues() {
  try {
    const raw = localStorage.getItem(DEMO_ISSUES_STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) : {};

    return saved && typeof saved === "object" && !Array.isArray(saved)
      ? saved
      : {};
  } catch (error) {
    console.warn("Demo issue decisions could not be loaded:", error);
    return {};
  }
}

function saveDemoIssues(issues) {
  try {
    const saved = {};

    issues.forEach(issue => {
      const id = String(issue.id || issue.issue_id || "");
      const fixture = demoIssues.find(item => item.id === id);

      if (fixture && id) {
        saved[id] = {
          state: issue.state,
          verification_outcome: issue.verification_outcome
        };
      }
    });

    localStorage.setItem(
      DEMO_ISSUES_STORAGE_KEY,
      JSON.stringify(saved)
    );

    return true;
  } catch (error) {
    console.warn("Demo issue decisions could not be saved:", error);
    return false;
  }
}

function readSavedDemoScans() {
  try {
    const raw = localStorage.getItem(DEMO_STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) : [];
    return Array.isArray(saved) ? saved : [];
  } catch (error) {
    console.warn("Demo scan history could not be loaded:", error);
    return [];
  }
}

function saveDemoScans(scans) {
  try {
    const fixtureIds = new Set(demoScans.map(scan => scan.id));
    const savedScans = scans.filter(scan => !fixtureIds.has(scan.id));

    localStorage.setItem(
      DEMO_STORAGE_KEY,
      JSON.stringify(savedScans.slice(0, 20))
    );

    return true;
  } catch (error) {
    console.warn("Demo scan history could not be saved:", error);
    return false;
  }
}

function nextDemoScanId(scans) {
  const highest = scans.reduce((max, scan) => {
    const match = String(scan.id || "").match(/^DEMO-(\d+)$/);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);

  return `DEMO-${String(highest + 1).padStart(3, "0")}`;
}

const isDemo=()=>$("#demoMode").checked;
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
function setModeUI(){
 const demo=isDemo();$("#modeLabel").textContent=demo?"Demo mode":"Live API";$("#dataBanner").hidden=!demo;$("#footerMode").textContent=demo?"DEMO ENVIRONMENT":"LIVE API";$("#scanModeFoot").textContent=demo?"Demo mode — no network request is made.":`API: ${window.OmniSightAPI.baseUrl}`;
}

function renderMetrics() {
  const d = data.dashboard || {};
  const demo = isDemo();

  const countVerified = data.issues.filter(
    i => normalizeState(i.state || i.verification_state || i.status) === "verified"
  ).length;

  const countAttention = data.issues.filter(
    i => normalizeState(i.state || i.verification_state || i.status) !== "verified"
  ).length;

  $("#metricScans").textContent = demo
    ? data.scans.length
    : val(d.total_scans, data.scans.length);

  $("#metricIssues").textContent = demo
    ? data.issues.length
    : val(d.issues_found, data.issues.length);

  $("#metricVerified").textContent = demo
    ? countVerified
    : val(d.verified_resolved, countVerified);

  $("#metricAttention").textContent = demo
    ? countAttention
    : val(d.needs_attention, countAttention);

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
function renderIssues(){
 const filter=$("#statusFilter").value,q=$("#globalSearch").value.trim().toLowerCase();
 const list=data.issues.filter(i=>{const st=normalizeState(i.state||i.verification_state||i.status);return(filter==="all"||st===filter)&&(!q||`${i.id} ${i.title} ${i.type} ${i.viewport} ${i.description}`.toLowerCase().includes(q))});
 $("#issueSummary").textContent=`${list.length} issue${list.length===1?"":"s"}  ·  ${isDemo()?"sample records":"backend response"}`;
 $("#issueList").innerHTML=list.map(i=>{
 const id=i.id||i.issue_id;const view=i.viewport||i.viewport_size||"Not specified";const type=i.type||i.issue_type||"Unclassified";
 return `<article class="issue-row"><div class="issue-thumb" aria-hidden="true"><div class="thumb-top"><i></i><i></i><i></i></div><div class="thumb-content"><span></span><span></span><i></i></div></div><div class="issue-main"><div class="issue-title-line"><h3>${esc(i.title||"Untitled issue")}</h3>${severity(i.severity)}</div><p>${esc(i.description||i.summary||"No description was supplied by the backend.")}</p><div class="issue-meta"><span>${esc(id||"ID unavailable")}</span><span>${esc(type)}</span><span>${esc(view)}</span></div><div class="issue-states">${badge(i.state||i.verification_state||i.status)}<span class="evidence-hint">${i.before_screenshot||i.screenshot_url||i.evidence_screenshot?"Evidence available":"Evidence unavailable"}</span></div></div><div class="issue-actions"><button class="button button-small button-light" data-review="${esc(id)}">Review issue →</button></div></article>`;
 }).join("");
 $("#issuesState").hidden=list.length>0; if(!list.length)setState($("#issuesState"),"empty","No matching issues","Try a different status filter or search term.");
}
function renderAll(){renderMetrics();renderScans();renderStatus();renderIssues()}
async function loadData(){
 const generation=++loadGeneration;setModeUI();
if (isDemo()) {
  const savedScans = readSavedDemoScans();

  const combinedScans = [
    ...savedScans,
    ...demoScans.map(scan => ({ ...scan }))
  ];

  const uniqueScans = [
    ...new Map(
      combinedScans.map(scan => [String(scan.id), scan])
    ).values()
  ];

  data = {
    scans: uniqueScans.slice(0, 20),
    issues: demoIssues.map(issue => ({
  ...issue,
  ...(readSavedDemoIssues()[issue.id] || {})
})),
    targets: [
      { id: "demo-overflow", name: "Demo target — mobile overflow" },
      { id: "demo-hidden", name: "Demo target — hidden control" }
    ],
    dashboard: {
      total_scans: uniqueScans.length,
      issues_found: demoIssues.length,
      verified_resolved: 0,
      needs_attention: demoIssues.length
    }
  };
  renderAll();
  fillTargets();
    clearState($("#dashboardState"));
  return;
}
 setState($("#dashboardState"),"loading","Loading dashboard","Requesting current scan and issue data from the backend.");
 $("#metricGrid").classList.add("is-loading");
 try{
  const results=await Promise.all([window.OmniSightAPI.dashboard(),window.OmniSightAPI.scans(),window.OmniSightAPI.issues(),window.OmniSightAPI.targets()]);
  if(generation!==loadGeneration)return;
  data={dashboard:results[0]||{},scans:normalizeArray(results[1]),issues:normalizeArray(results[2]),targets:normalizeTargets(results[3])};
  renderAll();fillTargets();clearState($("#dashboardState"));
  if(!data.scans.length&&!data.issues.length)setState($("#dashboardState"),"empty","No data yet","The backend returned no scans or issues. Start a scan to begin.");
 }catch(error){
  if(generation!==loadGeneration)return;
  data={dashboard:null,scans:[],issues:[],targets:[]};renderAll();fillTargets();
  setState($("#dashboardState"),"error","Could not load live data",error.message+" Confirm the backend routes in api.js match your teammate's API contract.");
  setState($("#issuesState"),"error","Issues unavailable",error.message);setState($("#historyState"),"error","History unavailable",error.message);
 }finally{$("#metricGrid").classList.remove("is-loading")}
}
function normalizeArray(v){return Array.isArray(v)?v:Array.isArray(v?.items)?v.items:Array.isArray(v?.results)?v.results:[]}
function normalizeTargets(v){return normalizeArray(v).map(t=>({id:t.id??t.target_id??t.url,name:t.name??t.label??t.url??t.target_url??String(t.id)}))}
function fillTargets(){
 const sel=$("#target"),old=sel.value;
 sel.innerHTML="";
 if(isDemo()){
  data.targets.forEach(t=>sel.add(new Option(t.name,t.id)));$("#targetHelp").textContent="Sample targets only. No site is accessed in demo mode.";return;
 }
 if(!data.targets.length){sel.add(new Option("No configured targets available",""));$("#targetHelp").textContent="The backend returned no configured targets.";return}
 data.targets.forEach(t=>sel.add(new Option(t.name,t.id)));if(data.targets.some(t=>String(t.id)===old))sel.value=old;
 $("#targetHelp").textContent="Targets are provided by the backend.";
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
async function handleScan(e){
 e.preventDefault();const desktop=$("#desktopViewport").checked,mobile=$("#mobileViewport").checked;
 if(!desktop&&!mobile){$("#scanFeedback").textContent="Select at least one viewport.";return}
 if(!$("#target").value){$("#scanFeedback").textContent="Choose a configured target first.";return}
 const btn=$("#runScanButton");btn.disabled=true;btn.innerHTML='<span class="spinner"></span> Request pending…';$("#scanFeedback").textContent="";
 try{
if (isDemo()) {
  const scan = {
    id: nextDemoScanId(data.scans),
    target: $("#target").selectedOptions[0]?.textContent || "Demo target",
    created_at: new Date().toLocaleString(),
    viewports: [
      desktop ? "Desktop" : null,
      mobile ? "Mobile" : null
    ].filter(Boolean),
    status: "demo not executed",
    issue_count: 0
  };

  data.scans.unshift(scan);
  data.scans = data.scans.slice(0, 20);
  saveDemoScans(data.scans);
  renderAll();


   $("#scanFeedback").textContent="Demo request recorded locally only. No website was accessed and no scan was run.";toast("Demo record created  no real scan executed.");navigate("history");
  }else{
   const result=await window.OmniSightAPI.createScan({target_id:$("#target").value,viewports:[desktop?"desktop":null,mobile?"mobile":null].filter(Boolean)});
   $("#scanFeedback").textContent=`Scan request accepted${result?.id||result?.scan_id?` (${result.id||result.scan_id})`:""}. Refreshing backend data.`;toast("Scan request sent to backend.");await loadData();navigate("history");
  }
 }catch(error){$("#scanFeedback").textContent=`Scan request failed: ${error.message}`;toast("Scan request failed.");}
 finally{btn.disabled=false;btn.innerHTML='Run scan <span>→</span>'}
}
async function reviewAction(action){
 if(!currentReview)return;const id=currentReview.id||currentReview.issue_id,buttons=$$("#reviewActions button");buttons.forEach(b=>b.disabled=true);
 try{
  if(isDemo()){
   const i=data.issues.find(x=>String(x.id||x.issue_id)===String(id));
   if(action==="approve"){i.state="applied";i.verification_outcome="Approved in demo only — no code changed."}
   else if(action==="reject"){i.state="detected";i.verification_outcome="Proposal rejected in demo only."}
   else {i.state="inconclusive";i.verification_outcome="No verification executed in demo mode."}
   saveDemoIssues(data.issues);
   renderAll();openReview(id);toast(action==="verify"?"Demo verification was not run.":"Demo state updated locally only.");return;
  }
  if(action==="approve")await window.OmniSightAPI.approveFix(id);
  else if(action==="reject")await window.OmniSightAPI.rejectFix(id);
  else await window.OmniSightAPI.verifyFix(id);
  toast("Backend accepted the request. Reloading current issue state.");await loadData();openReview(id);
 }catch(error){toast(`Request failed: ${error.message}`);buttons.forEach(b=>b.disabled=false)}
}
document.addEventListener("click",e=>{
 const page=e.target.closest("[data-page]");if(page){e.preventDefault();navigate(page.dataset.page);return}
 const review=e.target.closest("[data-review]");if(review){openReview(review.dataset.review);return}
 if(e.target.closest("#mobileMenu")){$("#sidebar").classList.toggle("open");return}
 if(e.target.closest("#refreshButton")){loadData();return}
 if(e.target.closest("#dismissBanner")){$("#dataBanner").hidden=true;return}
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
$("#demoMode").addEventListener("change",loadData);
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("#globalSearch").focus()}if(e.key==="Escape")$("#sidebar").classList.remove("open")});
loadData();
})();
