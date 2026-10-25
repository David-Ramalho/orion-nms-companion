let eventCursor=0,pendingScan=null,pendingSummary=false,lastProactive=0;
const kindLabels={note:'Anotação',place:'Lugar',goal:'Objetivo',lore:'Lore / ficção',summary:'Resumo gerado',observation:'Observação'};
function showPanel(expedition){$('chatPanel').hidden=expedition;$('expeditionPanel').hidden=!expedition;$('chatTab').classList.toggle('selected',!expedition);$('expeditionTab').classList.toggle('selected',expedition);if(expedition)refreshExpedition();}
$('chatTab').onclick=()=>showPanel(false);$('expeditionTab').onclick=()=>showPanel(true);
async function checked(url,options){const response=await apiFetch(url,options);const data=await response.json();if(!response.ok)throw Error(data.error||t("Não foi possível concluir."));return data;}
const jsonOptions=(data,method='POST')=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function report(error){$('hint').textContent=uiText(error.message);$('captureStatus').textContent=uiText(error.message);}
async function loadProfiles(){if(!localStorage.getItem('orion-profile')){const cfg=await checked('/api/settings');activeProfile=cfg.active_profile||'default';}const items=await checked('/api/profiles');if(!items.some(x=>x.id===activeProfile))activeProfile='default';$('profileSelect').replaceChildren(...items.map(x=>new Option(x.name,x.id)));$('profileSelect').value=activeProfile;$('exportJournal').href='/api/journal/export?profile='+encodeURIComponent(activeProfile);await checked('/api/active-profile',jsonOptions({}));localStorage.setItem('orion-profile',activeProfile);await loadFacts();}
$('newProfile').onclick=async()=>{const name=prompt(t("Nome do personagem / slot de save:"));if(!name?.trim())return;try{const result=await checked('/api/profiles',jsonOptions({name}));await switchProfile(result.id);await loadProfiles();}catch(e){report(e);}};
async function switchProfile(id){if(activeController){report(Error(t("Pare a resposta atual antes de trocar de personagem.")));$('profileSelect').value=activeProfile;return;}cancelMicrophone();stopVoice();activeProfile=id;localStorage.setItem('orion-profile',id);await checked('/api/active-profile',jsonOptions({}));$('messages').replaceChildren();await loadFacts();await refreshExpedition();$('exportJournal').href='/api/journal/export?profile='+encodeURIComponent(id);}
$('profileSelect').onchange=()=>switchProfile($('profileSelect').value).catch(report);
function node(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
async function loadJournal(){const profile=activeProfile;const items=await checked('/api/journal?q='+encodeURIComponent($('journalSearch').value));if(profile!==activeProfile)return;const box=$('journalEntries');box.replaceChildren();if(!items.length)box.append(node('p',t("Seu diário começa na próxima descoberta.")));
for(const item of items){const article=node('article');article.append(node('div',`${t(kindLabels[item.kind]||item.kind)} · ${item.source} · ${new Date(item.created_at).toLocaleString(uiDateLocale())} · ${item.status==='done'?t("Concluído"):t("Em aberto")}`,'meta'),node('h3',item.title));if(item.location)article.append(node('div',item.location,'meta'));article.append(node('p',item.content));if(item.attachment){const img=node('img');img.src=`/api/captures/${item.attachment}?profile=${activeProfile}`;img.alt=item.title;img.className='entry-image';article.append(img);}const controls=node('div',undefined,'buttonrow');if(item.kind==='goal'){const done=node('button',item.status==='done'?t("Reabrir"):t("Concluir objetivo"),'smallbtn');done.onclick=async()=>{await checked('/api/journal/'+item.id,jsonOptions({status:item.status==='done'?'open':'done'},'PATCH'));await refreshExpedition();};controls.append(done);}const remove=node('button',t("Excluir"),'quiet');remove.onclick=async()=>{if(!confirm(t("Excluir este registro?")))return;await checked('/api/journal/'+item.id,{method:'DELETE'});await refreshExpedition();};controls.append(remove);article.append(controls);box.append(article);}}
$('journalForm').onsubmit=async e=>{e.preventDefault();try{await checked('/api/journal',jsonOptions({kind:$('entryKind').value,title:$('entryTitle').value,location:$('entryLocation').value,content:$('entryContent').value}));$('entryTitle').value='';$('entryContent').value='';await refreshExpedition();}catch(error){report(error);}};
let searchTimer;$('journalSearch').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadJournal().catch(report),250);};
async function briefing(){const profile=activeProfile;const data=await checked('/api/briefing');if(profile!==activeProfile)return;const box=$('briefing');box.replaceChildren();if(!data.goals.length)box.append(node('p',t("Nenhum objetivo aberto. Registre seu próximo destino no diário.")));for(const item of data.goals.slice(0,5))box.append(node('div',item.title+' — '+item.content.slice(0,140),'brief-item'));if(data.recent[0])box.append(node('p',t("Último registro: ")+data.recent[0].title));}
async function gameStatus(){
  const profile=activeProfile,data=await checked('/api/game');if(profile!==activeProfile)return;
  const previous=$('saveCandidate').value;
  $('saveCandidate').replaceChildren(new Option(t("Selecione um save encontrado"),''),...(data.candidates||[]).map(x=>new Option(x.name,x.path)));
  $('saveCandidate').value=previous;
  if(document.activeElement!==$('savePath'))$('savePath').value=data.binding||'';
  const snap=data.snapshot,overview=$('saveOverview');overview.replaceChildren();
  $('saveStatus').textContent=snap?t("Lido em ")+new Date(snap.observed_at).toLocaleString(uiDateLocale())+' · '+snap.source:t("Nenhum save lido para este personagem. Vincule um arquivo abaixo.");
  if(data.watch?.error)$('saveStatus').textContent+=' · '+data.watch.error;
  if(!snap){$('gameSnapshot').textContent='';overview.append(node('p',t("Os dados do save aparecem aqui após a primeira leitura. O diário funciona independentemente."),'note'));return;}
  const p=snap.payload,bases=Array.isArray(p.bases)?p.bases:[],inventory=Array.isArray(p.inventory)?p.inventory:[];
  const rows=[['Units',p.Units],['Nanites',p.Nanites],[t("Bases lidas"),bases.length],[t("Itens / slots lidos"),inventory.length]];
  for(const [label,value] of rows){const item=node('div',undefined,'save-stat');item.append(node('span',label),node('b',value===undefined?t("Não disponível"):Number(value).toLocaleString(uiDateLocale())));overview.append(item);}
  if(!inventory.length)overview.append(node('p',t("Nenhum item extraído desta leitura. Isso não confirma um inventário vazio: o formato ou os campos deste save podem não ser suportados."),'note'));
  $('gameSnapshot').textContent=JSON.stringify({endereco:p.address,units:p.Units,nanites:p.Nanites,bases,slots_inventario:inventory.length,aviso:p.warning},null,2);
}
$('saveCandidate').onchange=()=>{$('savePath').value=$('saveCandidate').value;};
$('bindSave').onclick=async()=>{try{await checked('/api/game/bind',jsonOptions({path:$('savePath').value}));await gameStatus();}catch(e){report(e);}};
$('unbindSave').onclick=async()=>{try{await checked('/api/game/bind',jsonOptions({path:''}));await gameStatus();}catch(e){report(e);}};
$('syncSave').onclick=async()=>{try{await checked('/api/game/sync',jsonOptions({}));await gameStatus();}catch(e){report(e);}};
$('saveUpload').onchange=async()=>{const file=$('saveUpload').files[0];if(!file)return;const form=new FormData();form.append('save',file);try{await checked('/api/game/import',{method:'POST',body:form});await refreshExpedition();}catch(e){report(e);}finally{$('saveUpload').value='';}};
async function showScan(scan){if(scan.profile!==activeProfile)return;pendingScan=scan;$('scanImage').src=scan.image_url;$('scanText').value=scan.text;$('scanTitle').value=t("Observação do visor");$('scanNotice').textContent=scan.error||t("OCR pode errar nomes e números. Confirme apenas informações legíveis na imagem.");if(!$('scanDialog').open)$('scanDialog').showModal();}
async function requestCapture(form){$('captureStatus').textContent=t("Capturando e lendo texto…");const data=await checked('/api/capture',{method:'POST',body:form||undefined});$('captureStatus').textContent=t("Captura pronta para revisão.");await showScan(data);}
$('captureGame').onclick=()=>requestCapture().catch(report);
$('imageUpload').onchange=()=>{const file=$('imageUpload').files[0];if(!file)return;const form=new FormData();form.append('image',file);requestCapture(form).catch(report);$('imageUpload').value='';};
$('confirmScan').onclick=async()=>{if(!pendingScan||pendingScan.profile!==activeProfile)return;try{await checked('/api/journal',jsonOptions({kind:'observation',title:$('scanTitle').value,content:$('scanText').value,attachment:pendingScan.id}));$('scanDialog').close();pendingScan=null;await refreshExpedition();}catch(e){report(e);}};
$('cancelScan').onclick=()=>{$('scanDialog').close();pendingScan=null;};
async function diagnostics(){const data=await checked('/api/diagnostics');if(data.note)data.note=uiText(data.note);$('diagnostics').textContent=JSON.stringify(data,null,2);}
$('refreshDiagnostics').onclick=()=>diagnostics().catch(report);
async function refreshExpedition(){const results=await Promise.allSettled([loadJournal(),briefing(),gameStatus(),diagnostics()]);for(const result of results)if(result.status==='rejected')report(result.reason);}
$('askBriefing').onclick=()=>{showPanel(false);sendMessage(t("Ori, com base no diário e nos objetivos registrados, onde paramos e o que podemos explorar agora?"));};
$('sessionSummary').onclick=()=>{if(activeController)return;pendingSummary=true;showPanel(false);sendMessage(t("Faça um resumo curto desta sessão para o diário do capitão. Use apenas fatos registrados e nossa conversa; identifique sugestões e ficção. Inclua objetivos pendentes."));};
window.onReplyDone=async text=>{if(!pendingSummary)return;pendingSummary=false;try{await checked('/api/journal',jsonOptions({kind:'summary',title:t("Diário de bordo · ")+new Date().toLocaleDateString(uiDateLocale()),content:text}));}catch(e){report(e);}};
window.saveVoiceNote=async text=>{const match=text.match(/^(?:ori(?:on)?[,!:.]?\s+)?(?:registra|registre|anota|anote|guarda|guarde|remember|record|note|save)\s+(.+)/i);if(!match)return;const content=match[1];const kind=/^(?:objetivo|meta|goal|objective)[:\s]/i.test(content)?'goal':/^(?:lore|história|story)[:\s]/i.test(content)?'lore':'note';await checked('/api/journal',jsonOptions({kind,title:content.slice(0,90),content}));};
let subtitleTimer=null,latestSubtitle='';
window.updateSubtitle=text=>{latestSubtitle=text;if(subtitleTimer)return;subtitleTimer=setTimeout(()=>{subtitleTimer=null;checked('/api/subtitle',jsonOptions({text:latestSubtitle})).catch(()=>{});},250);};
$('refreshGoogle').onclick=async()=>{try{const data=await checked('/api/google/models');$('googleModels').replaceChildren(...data.models.map(x=>new Option(x,x)));$('hint').textContent=data.models.length+t(" modelos disponíveis para sua chave. Quotas e gratuidade são definidas no AI Studio.");}catch(e){report(e);}};
async function pollEvents(){try{const data=await checked('/api/desktop/events?after='+eventCursor);eventCursor=data.cursor;for(const e of data.events){if(e.profile!==activeProfile)continue;if(e.type==='transcript'){if(activeController){$('hint').textContent=t("Áudio transcrito; aguarde ou pare a resposta atual.");$('prompt').value=e.text;}else sendMessage(e.text).catch(report);}if(e.type==='stop'){pendingSummary=false;cancelMicrophone();stopVoice();}if(e.type==='notice'){$('hint').textContent=uiText(e.text);window.updateSubtitle(uiText(e.text));}if(e.type==='capture')await showScan(e.scan);if(e.type==='observation'&&!$('quietMode').checked&&Date.now()-lastProactive>180000&&!activeController){lastProactive=Date.now();addMessage('assistant',e.text);speak(e.text);}}}catch(e){}setTimeout(pollEvents,500);}
loadProfiles().then(async()=>{const state=await checked('/api/desktop/events?after=999999999');eventCursor=state.cursor;pollEvents();await refreshExpedition();}).catch(report);

window.onReplyFailed=()=>{pendingSummary=false;};
document.addEventListener('keydown',e=>{
  if(e.repeat)return;
  if(e.key==='F9'){e.preventDefault();pendingSummary=false;cancelMicrophone();stopVoice();}
});

document.addEventListener("orion:localechange",()=>{refreshExpedition().catch(report);});
