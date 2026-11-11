/* OmniSight scan-aware Q&A widget. Loaded by index.html. */
(() => {
  "use strict";
  if (document.getElementById("omniQaLauncher")) return;
  const style = document.createElement("style");
  style.textContent = `
    #omniQaLauncher{position:fixed;right:22px;bottom:22px;z-index:9998;border:0;border-radius:999px;padding:13px 19px;background:#111827;color:#fff;font-weight:700;box-shadow:0 8px 28px #0003;cursor:pointer}
    #omniQaPanel{position:fixed;right:22px;bottom:82px;z-index:9999;width:min(390px,calc(100vw - 28px));height:min(590px,calc(100vh - 120px));background:#fff;color:#111827;border:1px solid #dbe2ea;border-radius:16px;box-shadow:0 18px 60px #0003;display:none;flex-direction:column;overflow:hidden;font:14px/1.45 system-ui,sans-serif}
    #omniQaPanel.open{display:flex}#omniQaPanel header{padding:15px 16px;background:#111827;color:white;display:flex;justify-content:space-between;align-items:center}
    #omniQaPanel header button{background:transparent;border:0;color:white;font-size:20px;cursor:pointer}
    #omniQaControls{padding:12px;border-bottom:1px solid #e5e7eb}#omniQaControls select,#omniQaQuestion{width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:9px;background:#fff;color:#111827}
    #omniQaMessages{padding:12px;overflow:auto;flex:1;background:#f8fafc}#omniQaMessages .msg{white-space:pre-wrap;overflow-wrap:anywhere;padding:10px 12px;border-radius:11px;margin:0 0 10px;max-width:94%}
    #omniQaMessages .user{background:#e0e7ff;margin-left:auto}#omniQaMessages .bot{background:#fff;border:1px solid #e5e7eb}
    #omniQaForm{padding:12px;display:grid;gap:8px;border-top:1px solid #e5e7eb}#omniQaForm button{padding:10px;border:0;border-radius:9px;background:#111827;color:white;font-weight:700;cursor:pointer}
    #omniQaStatus{font-size:12px;color:#64748b}#omniQaForm button:disabled{opacity:.5;cursor:wait}
    @media(max-width:480px){#omniQaLauncher{right:14px;bottom:14px}#omniQaPanel{right:8px;bottom:70px;width:calc(100vw - 16px);height:calc(100vh - 90px)}}
  `;
  document.head.appendChild(style);
  const panel = document.createElement("section");
  panel.id = "omniQaPanel";
  panel.setAttribute("aria-label", "OmniSight Q&A assistant");
  panel.innerHTML = `
    <header><strong>OmniSight Q&A · Ollama</strong><button type="button" id="omniQaClose" aria-label="Close">×</button></header>
    <div id="omniQaControls"><label for="omniQaScan">Answer using scan</label><select id="omniQaScan"><option value="">Loading scan history…</option></select></div>
    <div id="omniQaMessages" aria-live="polite"><div class="msg bot">Ask about a completed scan: detected issues, mobile/desktop metrics, severity, or suggested next steps.</div></div>
    <form id="omniQaForm"><textarea id="omniQaQuestion" rows="2" maxlength="1200" placeholder="Why is the button off-screen on mobile?" required></textarea><button id="omniQaSend" type="submit">Ask about this scan</button><div id="omniQaStatus">Answers are grounded in the selected scan. Ollama must be running.</div></form>`;
  document.body.appendChild(panel);
  const launcher = document.createElement("button");
  launcher.id = "omniQaLauncher"; launcher.type = "button"; launcher.textContent = "Ask OmniSight";
  document.body.appendChild(launcher);
  const $ = id => document.getElementById(id);
  const apiBase = () => (window.OmniSightAPIConfig?.baseUrl || "http://127.0.0.1:8000/api").replace(/\/$/, "");
  const addMessage = (text, role) => { const node=document.createElement("div"); node.className="msg "+role; node.textContent=text; $("omniQaMessages").appendChild(node); $("omniQaMessages").scrollTop=$("omniQaMessages").scrollHeight; };
  async function loadScans(){
    const select=$("omniQaScan");
    try{
      const res=await fetch(apiBase()+"/scans"); if(!res.ok) throw new Error("Could not load scan history");
      const data=await res.json(); const rows=Array.isArray(data)?data:(data.scans||data.items||[]);
      select.innerHTML="";
      const done=rows.filter(s=>s.status==="completed");
      if(!done.length){select.innerHTML='<option value="">No completed scans yet</option>';return;}
      done.forEach(s=>{const opt=document.createElement("option");opt.value=s.scan_id||s.id;opt.textContent=(s.url||s.target||"Website")+" · "+(s.scan_id||s.id);select.appendChild(opt);});
    }catch(e){select.innerHTML='<option value="">Backend unavailable</option>';$("omniQaStatus").textContent=e.message;}
  }
  launcher.addEventListener("click",()=>{panel.classList.toggle("open");if(panel.classList.contains("open"))loadScans();});
  $("omniQaClose").addEventListener("click",()=>panel.classList.remove("open"));
  $("omniQaForm").addEventListener("submit",async e=>{
    e.preventDefault(); const question=$("omniQaQuestion").value.trim(),scan_id=$("omniQaScan").value;
    if(!scan_id){$("omniQaStatus").textContent="Select a completed scan first.";return;}
    if(!question)return;
    addMessage(question,"user"); $("omniQaQuestion").value=""; $("omniQaSend").disabled=true; $("omniQaStatus").textContent="Ollama is preparing an answer…";
    try{
      const res=await fetch(apiBase()+"/qa/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scan_id,question})});
      const data=await res.json(); if(!res.ok)throw new Error(data.detail||"Q&A request failed");
      addMessage(data.answer,"bot"); $("omniQaStatus").textContent="Source: selected scan metrics · "+data.model;
    }catch(err){addMessage("I couldn't answer: "+err.message,"bot");$("omniQaStatus").textContent="Check backend and Ollama connection.";}
    finally{$("omniQaSend").disabled=false;}
  });
})();
