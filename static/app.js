let activeProfile = localStorage.getItem('orion-profile') || 'default';
let currentSettings = {}, modelSettings = {}, parameterModel = '';
const $ = id => document.getElementById(id);
function apiFetch(url, options) {
  const parsed = new URL(url, location.origin);
  if (parsed.pathname.startsWith('/api/')) parsed.searchParams.set('profile', activeProfile);
  return fetch(parsed.pathname + parsed.search, options);
}
let micHeld = false, micOpening = false, micEpoch = 0, recordingLimit = null;
let activeController = null, recorder = null, holdTimer = null, speaking = false;
let speechBuffer = '', currentBubble = null, lastReplyEngine = '', turnEpoch = 0;
const parameterFields = {ollama_num_ctx:'contextSize',ollama_num_predict:'outputTokens',ollama_temperature:'temperature',ollama_num_thread:'threads',ollama_num_gpu:'gpuLayers',ollama_keep_alive:'keepAlive',provider_timeout:'providerTimeout',ollama_think:'modelThink'};
const parameterDefaults = {ollama_num_ctx:32768,ollama_num_predict:512,ollama_temperature:0.7,ollama_num_thread:0,ollama_num_gpu:-1,ollama_keep_alive:'5m',provider_timeout:180,ollama_think:false};
function readParameters() {
  const result = {};
  for (const [key,id] of Object.entries(parameterFields)) result[key] = key==='ollama_think' ? $(id).checked : key==='ollama_keep_alive' ? $(id).value.trim() : Number($(id).value);
  return result;
}
function displayParameters(values) {
  for (const [key,id] of Object.entries(parameterFields)) {
    const value = values[key] ?? parameterDefaults[key];
    if (key==='ollama_think') $(id).checked=!!value; else $(id).value=value;
  }
}
function cacheParameters() { if (parameterModel) modelSettings[parameterModel]=readParameters(); }
function selectModelParameters(name) {
  parameterModel=name;
  displayParameters({...parameterDefaults,...currentSettings,...(modelSettings[name]||{})});
  $('modelInfo').textContent=name ? t("Parâmetros deste modelo. Consulte os dados locais para ver sua capacidade.") : t("Selecione um modelo instalado no Ollama.");
}
function markSettingsDirty() {
  let notice=$('settingsNotice');
  if (!notice) { notice=document.createElement('p'); notice.id='settingsNotice'; notice.className='note'; $('saveSettings').before(notice); }
  notice.textContent=t("Alterações pendentes — salve para aplicar na próxima resposta.");
}
function addMessage(role,text='') {
  const row=document.createElement('div'); row.className='msg '+role;
  const who=document.createElement('div'); who.className='who'; who.textContent=role==='assistant'?'ORION':t("VOCÊ");
  if(role==='assistant'){const small=document.createElement('small');small.textContent='ORI · EXOSUIT';who.append(small);}
  const bubble=document.createElement('div');bubble.className='bubble';bubble.textContent=text;
  row.append(who,bubble);$('messages').append(row);$('messages').scrollTop=$('messages').scrollHeight;
  return bubble;
}
function renderVerifiedSave(details,data) {
  const wasOpen=details.open;details.replaceChildren();details._verifiedSave=data;
  const summary=document.createElement('summary');summary.textContent=t("Dados verificados do save");details.append(summary);
  const note=document.createElement('p');note.textContent=t("Referencia do aplicativo, separada da resposta da IA.");details.append(note);
  const list=document.createElement('dl');
  const rows=[['Units',data.currencies?.Units],['Nanites',data.currencies?.Nanites],['Quicksilver',data.currencies?.Quicksilver],[t("Bases lidas"),data.base_count],[t("Entradas de inventario reconhecidas"),data.inventory_count]];
  for(const [label,value] of rows){const term=document.createElement('dt'),definition=document.createElement('dd');term.textContent=label;definition.textContent=typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(uiDateLocale()):t("Desconhecido");list.append(term,definition);}
  details.append(list);
  if(data.observed_at){const stamp=document.createElement('p');const date=new Date(data.observed_at);stamp.textContent=t("Ultimo salvamento")+': '+(Number.isNaN(date.getTime())?data.observed_at:date.toLocaleString(uiDateLocale()));details.append(stamp);}
  const limits=document.createElement('p');limits.textContent=t("Snapshot historico; o inventario pode estar incompleto.");details.append(limits);
  if(data.warning){const warning=document.createElement('p');warning.textContent=t("O leitor registrou um aviso. Confira os detalhes do save.");details.append(warning);}
  details.open=wasOpen;
}
function attachVerifiedSave(bubble,data) {
  if(!data)return;
  let details=bubble.parentElement.querySelector('.verified-save');
  if(!details){details=document.createElement('details');details.className='verified-save';bubble.before(details);}
  renderVerifiedSave(details,data);
}
async function updateStatus() {
  try {
    const response=await apiFetch('/api/status'); if(!response.ok)throw Error(t("Status indisponível"));
    const s=await response.json(),models=s.ollama_models||[];
    $('lamp').className=s.ollama_online||s.gemini_key_set?'good':'';
    $('statusText').textContent=s.mode==='auto'?t("Salvo: Automático · local primeiro"):t("Salvo: ")+(s.mode==='ollama'?'Ollama':'Gemini')+(s.configured_model?' · '+s.configured_model:'');
    $('ollamaDot').className='dot '+(s.ollama_online?'good':'bad');
    $('ollamaLabel').textContent=s.ollama_online?t("Servidor online"):t("Sem conexão");
    $('geminiDot').className='dot '+(s.gemini_key_set?'good':'');
    $('geminiLabel').textContent=s.gemini_key_set?t("Chave salva"):t("Sem chave");
    const previous=$('model').value||currentSettings.ollama_model||'';
    $('model').replaceChildren();
    if(previous&&!models.includes(previous))$('model').append(new Option(previous+t(" · não listado"),previous));
    for(const name of models)$('model').append(new Option(name,name));
    if(!$('model').options.length)$('model').append(new Option(s.ollama_online?t("Nenhum modelo instalado"):t("Conecte o Ollama"),''));
    $('model').value=previous||models[0]||'';
    if(parameterModel!==$('model').value)selectModelParameters($('model').value);
  } catch(e){$('ollamaLabel').textContent=t("Status indisponível");}
}
function refreshVoices() {
  if(!('speechSynthesis' in window))return;
  const selected=$('voice').value||currentSettings.voice_name||'';
  $('voice').replaceChildren(new Option(t("Padrão do sistema"),''));
  for(const v of speechSynthesis.getVoices())$('voice').append(new Option(v.name+' · '+v.lang,v.name));
  $('voice').value=selected;
}
async function loadSettings() {
  try {
    const r=await apiFetch('/api/settings'); if(!r.ok)throw Error(t("Não foi possível carregar as configurações."));
    const c=await r.json();currentSettings=c;modelSettings=structuredClone(c.ollama_model_settings||{});
    $('language').value=c.stt_language||'auto';$('quietMode').checked=!!c.quiet_mode;$('ttsEnabled').checked=c.tts_enabled!==false;$('replyStyle').value=c.reply_style||'explorer';
    $('cloudSettings').open=c.provider_mode==='gemini';$('libnom').value=c.libnom_cli||'';$('provider').value=c.provider_mode;$('ollamaUrl').value=c.ollama_url;$('geminiModel').value=c.gemini_model;
    $('cloudFallback').checked=!!c.cloud_fallback;$('cloudConsent').checked=!!c.cloud_consent;$('rate').value=c.voice_rate;$('rateLabel').textContent=Number(c.voice_rate).toFixed(2)+'x';$('persona').value=c.system_prompt;$('stt').value=c.stt_model;
    refreshVoices();await updateStatus();
  } catch(e){$('hint').textContent=uiText(e.message);}
}
if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=refreshVoices;
let speechQueued=0;
function speak(text) {
  if(!text.trim()||!('speechSynthesis' in window)||!$('ttsEnabled').checked||speechQueued>=12)return;
  const utterance=new SpeechSynthesisUtterance(text.trim()),voice=speechSynthesis.getVoices().find(v=>v.name===$('voice').value);
  if(voice)utterance.voice=voice;
  utterance.lang=$('language').value==='pt'?'pt-BR':$('language').value==='en'?'en-US':voice?.lang||navigator.language;utterance.rate=Number($('rate').value);
  speaking=true;speechQueued++;
  const ended=()=>{speechQueued=Math.max(0,speechQueued-1);speaking=speechSynthesis.speaking;};
  utterance.onend=ended;utterance.onerror=ended;speechSynthesis.speak(utterance);
}
function queueSpeech(fragment,flush=false) {
  speechBuffer+=fragment;const boundary=/[.!?](?:["')\]]*)\s+/g;let match,start=0;
  while((match=boundary.exec(speechBuffer))){speak(speechBuffer.slice(start,match.index+match[0].trimEnd().length));start=boundary.lastIndex;}
  speechBuffer=speechBuffer.slice(start);if(flush&&speechBuffer.trim()){speak(speechBuffer);speechBuffer='';}
}
async function sendMessage(text) {
  text=text.trim();if(!text||activeController)return;
  const controller=new AbortController(),epoch=++turnEpoch;activeController=controller;
  $('send').disabled=true;$('hint').textContent=t("Preparando memória e carregando o modelo…");
  if('speechSynthesis' in window)speechSynthesis.cancel();speechQueued=0;speechBuffer='';
  let bubble=null;
  try {
    if(window.saveVoiceNote)await window.saveVoiceNote(text);
    if(controller.signal.aborted||epoch!==turnEpoch)return;
    $('prompt').value='';addMessage('user',text);bubble=addMessage('assistant');currentBubble=bubble;bubble.classList.add('streaming');
    const response=await apiFetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,ui_locale:window.uiLocale()}),signal:controller.signal});
    if(!response.ok){let e;try{e=await response.json();}catch{e={};}throw Error(e.error||'HTTP '+response.status);}
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',failed=false;
    const consume=line=>{
      if(!line||epoch!==turnEpoch)return;
      const item=JSON.parse(line);
      if(item.type==='start'){
        attachVerifiedSave(bubble,item.verified_save);
        lastReplyEngine=t(item.provider)+(item.model?' · '+item.model:'');const badge=document.createElement('small');badge.className='engine-badge';badge.textContent=lastReplyEngine;bubble.parentElement.querySelector('.who').append(badge);
        $('hint').textContent=t("Aguardando ")+lastReplyEngine+t(" · o primeiro carregamento pode demorar");
      }
      if(item.type==='delta'){bubble.textContent+=item.text;queueSpeech(item.text);window.updateSubtitle?.(bubble.textContent);$('messages').scrollTop=$('messages').scrollHeight;$('hint').textContent=t("Respondendo: ")+lastReplyEngine;}
      if(item.type==='done'){bubble.classList.remove('streaming');queueSpeech('',true);window.onReplyDone?.(item.text);$('hint').textContent=t("Última resposta: ")+lastReplyEngine+t(" · pronto");}
      if(item.type==='error'){attachVerifiedSave(bubble,item.verified_save);failed=true;window.onReplyFailed?.();if('speechSynthesis' in window)speechSynthesis.cancel();speechQueued=0;speechBuffer='';bubble.classList.remove('streaming');bubble.textContent=uiText(item.message);$('hint').textContent=t("Confira conexão, modelo e tempo de espera em Sistemas de IA.");}
      if(item.type==='cancelled'){bubble.classList.remove('streaming');$('hint').textContent=t("Resposta interrompida.");}
    };
    while(true){const {value,done}=await reader.read();if(done)break;pending+=decoder.decode(value,{stream:true});const lines=pending.split('\n');pending=lines.pop();for(const line of lines)consume(line);}
    pending+=decoder.decode();if(pending.trim())consume(pending);
    if(failed)window.onReplyFailed?.();
  } catch(err){
    window.onReplyFailed?.();
    if(err.name!=='AbortError'&&epoch===turnEpoch){if(bubble)bubble.textContent=t("Falha de conexão: ")+err.message;$('hint').textContent=uiText(err.message);}
  } finally {
    bubble?.classList.remove('streaming');
    if(activeController===controller){activeController=null;$('send').disabled=false;}
  }
}
function stopVoice() {
  activeController?.abort();
  apiFetch('/api/turn/stop',{method:'POST'}).catch(()=>{});
  if('speechSynthesis' in window)speechSynthesis.cancel();speechQueued=0;speechBuffer='';
  currentBubble?.classList.remove('streaming');$('hint').textContent=t("Resposta e voz interrompidas.");
}
function cancelMicrophone() {
  micEpoch++;micHeld=false;clearTimeout(holdTimer);clearTimeout(recordingLimit);
  if(recorder?.state==='recording')recorder.stop();
}
async function startRecording() {
  if(micOpening||recorder?.state==='recording')return;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){$('hint').textContent=t("Use Chrome ou Edge para gravar pelo microfone.");return;}
  micOpening=true;const epoch=++micEpoch;let stream;
  try {
    stopVoice();stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
    if(!micHeld||epoch!==micEpoch){stream.getTracks().forEach(t=>t.stop());return;}
    const mime=['audio/webm;codecs=opus','audio/webm','audio/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
    const recording=new MediaRecorder(stream,mime?{mimeType:mime}:undefined),chunks=[];recorder=recording;
    recording.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recording.onstop=async()=>{
      clearTimeout(recordingLimit);stream.getTracks().forEach(t=>t.stop());$('mic').classList.remove('recording');
      if(epoch!==micEpoch)return;
      $('hint').textContent=t("Transcrevendo no PC… o primeiro uso baixa o modelo de voz.");
      try {
        const form=new FormData();form.append('audio',new Blob(chunks,{type:recording.mimeType||'audio/webm'}),'speech.webm');
        const response=await apiFetch('/api/transcribe',{method:'POST',body:form});const data=await response.json();
        if(epoch!==micEpoch)return;if(!response.ok)throw Error(data.error||t("Falha na transcrição."));
        if(data.text){if(activeController){$('prompt').value=data.text;$('hint').textContent=t("Transcrição pronta. Envie quando a resposta terminar.");}else await sendMessage(data.text);}else $('hint').textContent=t("Nenhuma fala detectada. Segure o microfone e tente novamente.");
      }catch(e){if(epoch===micEpoch)$('hint').textContent=uiText(e.message);}
    };
    recording.start(300);$('mic').classList.add('recording');$('hint').textContent=t("Gravando · solte para enviar · limite de 60 segundos");
    recordingLimit=setTimeout(()=>{micHeld=false;stopRecording();},60000);
  }catch(e){stream?.getTracks().forEach(t=>t.stop());$('hint').textContent=t("Microfone: ")+e.message;}
  finally{micOpening=false;}
}
function stopRecording(){if(recorder?.state==='recording')recorder.stop();}
$('send').onclick=()=>sendMessage($('prompt').value);
$('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage($('prompt').value);}});
$('mic').addEventListener('pointerdown',e=>{e.preventDefault();micHeld=true;$('mic').setPointerCapture(e.pointerId);holdTimer=setTimeout(startRecording,170);});
for(const name of ['pointerup','pointercancel'])$('mic').addEventListener(name,()=>{micHeld=false;clearTimeout(holdTimer);stopRecording();});
$('stop').onclick=()=>{cancelMicrophone();stopVoice();};$('refresh').onclick=updateStatus;
$('rate').oninput=()=>$('rateLabel').textContent=Number($('rate').value).toFixed(2)+'x';
$('model').onchange=()=>{cacheParameters();selectModelParameters($('model').value);markSettingsDirty();};
$('modelDefaults').onclick=async()=>{
  if(!$('model').value)return;
  $('modelDefaults').disabled=true;$('modelInfo').textContent=t("Consultando metadados locais…");
  const name=$('model').value;
  try{
    const response=await apiFetch('/api/models/details?model='+encodeURIComponent(name));const data=await response.json();if(!response.ok)throw Error(data.error||t("Falha ao consultar o modelo."));
    if($('model').value!==name)return;
    const details=data.details||data;
    $('modelInfo').textContent=[details.family,details.parameter_size,details.quantization_level,details.context_length?t("Capacidade informada: ")+Number(details.context_length).toLocaleString(uiDateLocale())+t(" tokens"):null].filter(Boolean).join(' · ')||t("O modelo não informou sua capacidade de contexto.");
    // Advertised maximum is informational. Use the Modelfile default, or let Ollama choose.
    const defaults=details.model_defaults||{};
    $('contextSize').value=Number(details.default_context_length ?? defaults.num_ctx)||0;
    for(const [key,id] of Object.entries({num_predict:'outputTokens',temperature:'temperature',num_thread:'threads',num_gpu:'gpuLayers'})){
      if(defaults[key]!==undefined&&Number.isFinite(Number(defaults[key])))$(id).value=Number(defaults[key]);
    }
    cacheParameters();markSettingsDirty();
    $('modelInfo').textContent+=t(" · Padrões aplicados. Salve para usar.");
  }catch(e){$('modelInfo').textContent=uiText(e.message);}finally{$('modelDefaults').disabled=false;}
};
$('unloadModel').onclick=async()=>{
  try{const response=await apiFetch('/api/models/unload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:$('model').value})});const data=await response.json();if(!response.ok)throw Error(data.error||t("Não foi possível liberar o modelo."));$('modelInfo').textContent=t("Modelo liberado da memória. A próxima resposta fará um novo carregamento.");}catch(e){$('modelInfo').textContent=uiText(e.message);}
};
$('saveSettings').onclick=async()=>{
  const checked=$('cloudFallback').checked,consent=$('cloudConsent').checked;
  if((checked||consent)&&!currentSettings.cloud_consent&&!confirm(t("Gemini envia suas perguntas e memórias selecionadas para o Google. Consulte as condições, quotas e cobrança do seu projeto no AI Studio. Permitir processamento na nuvem?")))return;
  cacheParameters();
  const data={...readParameters(),ollama_model_settings:modelSettings,stt_language:$('language').value,quiet_mode:$('quietMode').checked,tts_enabled:$('ttsEnabled').checked,reply_style:$('replyStyle').value,libnom_cli:$('libnom').value,provider_mode:$('provider').value,ollama_url:$('ollamaUrl').value,ollama_model:$('model').value,gemini_model:$('geminiModel').value,cloud_fallback:checked,cloud_consent:consent,voice_rate:Number($('rate').value),voice_name:$('voice').value,stt_model:$('stt').value,system_prompt:$('persona').value};
  $('saveSettings').disabled=true;
  try{const response=await apiFetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),result=await response.json();if(!response.ok)throw Error(result.error||t("Falha ao salvar."));currentSettings=result.settings||data;$('settingsNotice')?.remove();$('hint').textContent=t("Configurações salvas. Valem para a próxima resposta.");await updateStatus();}
  catch(e){$('hint').textContent=uiText(e.message);}finally{$('saveSettings').disabled=false;}
};
$('saveKey').onclick=async()=>{const api_key=$('apiKey').value.trim();if(!api_key)return;try{const r=await apiFetch('/api/credential',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key})}),d=await r.json();if(!r.ok)throw Error(d.error||t("Falha ao salvar a chave."));$('hint').textContent=t("Chave Gemini salva no Gerenciador de Credenciais do Windows.");$('apiKey').value='';updateStatus();}catch(e){$('hint').textContent=uiText(e.message);}};
$('addFact').onclick=async()=>{const content=prompt(t("O que Ori deve lembrar nas próximas explorações?"));if(!content?.trim())return;try{const r=await apiFetch('/api/memory/facts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});if(!r.ok)throw Error(t("Não foi possível guardar a memória."));await loadFacts(false);}catch(e){$('hint').textContent=uiText(e.message);}};
$('clear').onclick=async()=>{
  if(!confirm(t("Iniciar uma nova conversa neste personagem? O diário, as memórias e o save vinculado serão mantidos.")))return;
  $('clear').disabled=true;turnEpoch++;cancelMicrophone();stopVoice();window.onReplyFailed?.();
  try{const response=await apiFetch('/api/memory/clear-history',{method:'POST'});const data=await response.json();if(!response.ok)throw Error(data.error||t("Falha ao limpar conversa."));$('messages').replaceChildren();currentBubble=null;lastReplyEngine='';$('hint').textContent=t("Nova conversa. Diário e memórias preservados.");}
  catch(e){$('hint').textContent=uiText(e.message);}finally{$('clear').disabled=false;}
};
async function loadFacts(restoreHistory=true){
  const profile=activeProfile,r=await apiFetch('/api/memory');if(!r.ok)throw Error(t("Não foi possível carregar a memória."));const d=await r.json();if(profile!==activeProfile)return;
  const box=$('facts');box.replaceChildren();
  if(!d.facts.length){const p=document.createElement('div');p.className='empty';p.textContent=t("Sem memórias fixas. Use + MEMÓRIA para guardar algo.");box.append(p);}
  else for(const fact of d.facts){const el=document.createElement('div');el.className='fact';const span=document.createElement('span');span.textContent=fact;el.append(span);box.append(el);}
  if(restoreHistory&&!activeController){$('messages').replaceChildren();for(const item of d.history)addMessage(item.role==='assistant'?'assistant':'user',item.content);}
}
for(const id of ['provider','geminiModel','cloudConsent','cloudFallback',...Object.values(parameterFields),'ollamaUrl','language','quietMode','ttsEnabled','replyStyle','voice','rate','persona','stt'])$(id).addEventListener('change',markSettingsDirty);
loadSettings();setInterval(updateStatus,30000);

document.addEventListener("orion:localechange",()=>{refreshVoices();updateStatus();loadFacts(false).catch(()=>{});});

document.addEventListener("orion:localechange",()=>{for(const details of document.querySelectorAll(".verified-save"))renderVerifiedSave(details,details._verifiedSave);});
