/* OmniSight scan-aware Q&A workspace. */
(() => {
  "use strict";
  if (document.getElementById("omniQaLauncher")) return;
  const style = document.createElement("style");
  style.textContent = `
    #omniQaLauncher{position:fixed;right:22px;bottom:22px;z-index:9998;border:0;border-radius:999px;padding:14px 20px;background:#2563eb;color:#fff;font-weight:750;box-shadow:0 8px 28px #0005;cursor:pointer}
    #omniQaPanel{position:fixed;inset:5vh 5vw;z-index:9999;background:#111827;color:#f8fafc;border:1px solid #374151;border-radius:18px;box-shadow:0 22px 80px #0009;display:none;flex-direction:column;overflow:hidden;font:14px/1.5 system-ui,sans-serif}
    #omniQaPanel.open{display:flex}
    #omniQaPanel header{padding:17px 22px;background:#0b1220;color:white;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #334155}
    #omniQaPanel header strong{font-size:18px}#omniQaPanel header button{background:#263449;border:0;color:white;border-radius:8px;font-size:22px;width:36px;height:36px;cursor:pointer}
    #omniQaIntro{padding:14px 22px;color:#cbd5e1;background:#172033;border-bottom:1px solid #334155}
    #omniQaControls{padding:14px 22px;display:flex;gap:12px;align-items:end;border-bottom:1px solid #334155;flex-wrap:wrap}
    #omniQaControls label{display:grid;gap:6px;flex:1;min-width:220px;color:#cbd5e1;font-weight:650}
    #omniQaControls select,#omniQaQuestion,#omniQaImage{width:100%;box-sizing:border-box;padding:12px;border:1px solid #475569;border-radius:10px;background:#0f172a;color:#f8fafc}
    #omniQaImage{max-width:320px}#omniQaUploadLabel{display:grid;gap:6px;min-width:220px;color:#cbd5e1;font-weight:650}
    #omniQaRefresh{padding:12px 16px;border:1px solid #475569;border-radius:10px;background:#263449;color:white;cursor:pointer}
    #omniQaMessages{padding:20px 22px;overflow:auto;flex:1;background:#0f172a}
    #omniQaMessages .msg{white-space:pre-wrap;overflow-wrap:anywhere;padding:13px 16px;border-radius:13px;margin:0 0 14px;max-width:min(850px,92%);line-height:1.6}
    #omniQaMessages .user{background:#1d4ed8;color:white;margin-left:auto}
    #omniQaMessages .bot{background:#1e293b;color:#f8fafc;border:1px solid #334155}
    #omniQaMessages .meta{font-size:11px;color:#94a3b8;margin:-8px 0 12px}
    #omniQaForm{padding:16px 22px;display:grid;grid-template-columns:1fr auto;gap:10px;border-top:1px solid #334155;background:#111827}
    #omniQaQuestion{resize:vertical;min-height:54px}#omniQaSend{padding:12px 22px;border:0;border-radius:10px;background:#2563eb;color:white;font-weight:750;cursor:pointer}
    #omniQaStatus{grid-column:1/-1;font-size:12px;color:#94a3b8}#omniQaSend:disabled{opacity:.5;cursor:wait}
    @media(max-width:650px){#omniQaPanel{inset:8px;border-radius:12px}#omniQaForm{grid-template-columns:1fr}#omniQaSend{width:100%}#omniQaLauncher{right:14px;bottom:14px}}
  `;
  document.head.appendChild(style);
  const panel=document.createElement("section");panel.id="omniQaPanel";panel.setAttribute("role","dialog");panel.setAttribute("aria-modal","true");panel.setAttribute("aria-label","OmniSight AI Q&A workspace");
  panel.innerHTML=`
    <header><strong>OmniSight · AI Q&A Assistant</strong><button type="button" id="omniQaClose" aria-label="Close assistant">×</button></header>
    <div id="omniQaIntro">Ask about a completed website scan, or upload a screenshot for direct visual analysis. Answers use the configured Ollama vision model.</div>
    <div id="omniQaControls"><label for="omniQaScan">Website scan evidence (optional)<select id="omniQaScan"><option value="">Loading scan history…</option></select></label><label id="omniQaUploadLabel" for="omniQaImage">Or upload a screenshot (PNG, JPG, WebP)<input id="omniQaImage" type="file" accept="image/png,image/jpeg,image/webp"></label><button type="button" id="omniQaRefresh">Refresh scans</button></div>
    <div id="omniQaMessages" aria-live="polite"><div class="msg bot">Welcome to OmniSight Q&A. Select a completed scan above, then ask about detected issues, viewport differences, measurements, or possible fixes.</div></div>
    <form id="omniQaForm"><textarea id="omniQaQuestion" rows="2" maxlength="1200" placeholder="Example: Why does this page overflow on mobile, and how can I fix it?" required></textarea><button id="omniQaSend" type="submit">Ask Ollama ↗</button><div id="omniQaStatus">Waiting for a question. Ollama must be running on the backend host.</div></form>`;
  document.body.appendChild(panel);
  const launcher=document.createElement("button");launcher.id="omniQaLauncher";launcher.type="button";launcher.textContent="Ask OmniSight AI";launcher.setAttribute("aria-haspopup","dialog");document.body.appendChild(launcher);
  const nav=document.querySelector(".sidebar nav");
  if(nav&&!document.getElementById("omniQaNav")){const b=document.createElement("button");b.id="omniQaNav";b.type="button";b.className="nav-link";b.innerHTML='<span class="nav-icon">✦</span>AI Q&A';nav.appendChild(b);b.addEventListener("click",openAssistant);}
  const $=id=>document.getElementById(id);
  const apiBase=()=> (window.OmniSightAPIConfig?.baseUrl||"http://127.0.0.1:8000/api").replace(/\/$/,"");
  function addMessage(value,role){const node=document.createElement("div");node.className="msg "+role;node.textContent=value;$("omniQaMessages").appendChild(node);$("omniQaMessages").scrollTop=$("omniQaMessages").scrollHeight;}
  async function loadScans(){
    const select=$("omniQaScan");select.innerHTML='<option value="">Loading completed scans…</option>';
    try{
      const res=await fetch(apiBase()+"/scans");if(!res.ok)throw new Error("Scan history request failed (HTTP "+res.status+")");
      const data=await res.json();const rows=Array.isArray(data)?data:(data.scans||data.items||[]);
      const done=rows.filter(s=>String(s.status||s.state||"").toLowerCase()==="completed");
      select.innerHTML="";
      if(!done.length){select.innerHTML='<option value="">No completed scans — run a scan first</option>';$("omniQaStatus").textContent="No completed scans found. Run a scan, then refresh this list.";return;}
      done.forEach((s,i)=>{const id=s.scan_id||s.id;if(!id)return;const o=document.createElement("option");o.value=id;o.textContent=(s.url||s.target||"Website")+" · "+id;select.appendChild(o);});
      if(select.options.length){select.selectedIndex=0;$("omniQaStatus").textContent="Loaded "+select.options.length+" completed scan(s). Latest scan selected.";}
    }catch(e){select.innerHTML='<option value="">Could not load scans</option>';$("omniQaStatus").textContent=e.message;}
  }
  function openAssistant(){panel.classList.add("open");loadScans();$("omniQaQuestion").focus();}
  launcher.addEventListener("click",openAssistant);$("omniQaClose").addEventListener("click",()=>panel.classList.remove("open"));$("omniQaRefresh").addEventListener("click",loadScans);
  document.addEventListener("keydown",e=>{if(e.key==="Escape")panel.classList.remove("open");});
  $("omniQaForm").addEventListener("submit",async e=>{
    e.preventDefault();
    const question=$("omniQaQuestion").value.trim(),scan_id=$("omniQaScan").value,file=$("omniQaImage").files[0];
    if(!question)return;
    if(!file&&!scan_id){$("omniQaStatus").textContent="Select a completed scan or upload a screenshot.";return;}
    if(file&&file.size>8*1024*1024){$("omniQaStatus").textContent="Screenshot must be 8 MB or smaller.";return;}
    addMessage(question,"user");$("omniQaQuestion").value="";$("omniQaSend").disabled=true;
    $("omniQaStatus").textContent=file?"Ollama is analysing your screenshot…":"Ollama is analysing the selected scan…";
    try{
      let endpoint="/qa/ask",body;
      if(file){
        const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error("Could not read screenshot file."));reader.readAsDataURL(file);});
        endpoint="/qa/screenshot";
        body={question,image_base64:String(dataUrl).split(",")[1],mime_type:file.type||"image/png"};
      }else body={scan_id,question};
      const res=await fetch(apiBase()+endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      const data=await res.json();if(!res.ok)throw new Error(data.detail||"Q&A request failed");
      addMessage(data.answer||"The model returned an empty answer.","bot");
      const meta=document.createElement("div");meta.className="meta";meta.textContent="Evidence: "+(data.evidence_scope||"selected scan")+" · Model: "+(data.model||"Ollama");$("omniQaMessages").appendChild(meta);$("omniQaMessages").scrollTop=$("omniQaMessages").scrollHeight;
      $("omniQaStatus").textContent=file?"Screenshot analysis completed.":"Answer received from Ollama for scan "+scan_id+".";
      if(file)$("omniQaImage").value="";
    }catch(err){addMessage("Unable to answer: "+err.message,"bot");$("omniQaStatus").textContent="Check the FastAPI backend and Ollama connection.";}
    finally{$("omniQaSend").disabled=false;$("omniQaQuestion").focus();}
  });
})();
