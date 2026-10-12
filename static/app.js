const $ = (id) => document.getElementById(id);
let activeController = null, recorder = null, chunks = [], holdTimer = null, speaking = false;
let speechBuffer = '', currentBubble = null;

function addMessage(role, text = '') {
  const row = document.createElement('div'); row.className = `msg ${role}`;
  const who = document.createElement('div'); who.className = 'who'; who.textContent = role === 'assistant' ? 'ORION' : 'YOU';
  if (role === 'assistant') { const small = document.createElement('small'); small.textContent = 'ORI · EXOSUIT'; who.appendChild(small); }
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  row.append(who, bubble); $('messages').appendChild(row); $('messages').scrollTop = $('messages').scrollHeight;
  return bubble;
}
function updateStatus() {
  fetch('/api/status').then(r => r.json()).then(s => {
    $('lamp').className = s.ollama_online || s.gemini_key_set ? 'good' : '';
    $('statusText').textContent = s.ollama_online ? 'Local link ready' : s.gemini_key_set ? 'Cloud key ready' : 'Awaiting AI link';
    $('ollamaDot').className = `dot ${s.ollama_online ? 'good' : 'bad'}`;
    $('ollamaLabel').textContent = s.ollama_online ? 'Online' : 'Offline';
    $('geminiDot').className = `dot ${s.gemini_key_set ? 'good' : ''}`;
    $('geminiLabel').textContent = s.gemini_key_set ? 'Key stored' : 'Key not set';
    const previous = $('model').value;
    $('model').replaceChildren();
    if (!s.ollama_models.length) { const o = document.createElement('option'); o.value = ''; o.textContent = s.ollama_online ? 'No installed models' : 'Ollama offline'; $('model').append(o); }
    for (const name of s.ollama_models) { const o = document.createElement('option'); o.value = name; o.textContent = name; $('model').append(o); }
    $('model').value = s.ollama_models.includes(previous) ? previous : (s.ollama_models[0] || '');
  }).catch(() => {});
}
function loadSettings() {
  fetch('/api/settings').then(r => r.json()).then(c => {
    $('provider').value = c.provider_mode; $('ollamaUrl').value = c.ollama_url; $('geminiModel').value = c.gemini_model;
    $('cloudFallback').checked = !!c.cloud_fallback; $('cloudConsent').checked = !!c.cloud_consent; $('rate').value = c.voice_rate; $('rateLabel').textContent = `${Number(c.voice_rate).toFixed(2)}×`; $('persona').value = c.system_prompt;
    $('stt').value = c.stt_model;
    setTimeout(() => { if (c.ollama_model) $('model').value = c.ollama_model; }, 500);
    if ('speechSynthesis' in window) {
      const voices = speechSynthesis.getVoices();
      $('voice').replaceChildren(new Option('System default', ''));
      for (const v of voices) { const o = document.createElement('option'); o.value = v.name; o.textContent = `${v.name} · ${v.lang}`; $('voice').append(o); }
      $('voice').value = c.voice_name || '';
    }
  });
}
if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = loadSettings;
function speak(text) {
  if (!text.trim() || !('speechSynthesis' in window)) return;
  const utterance = new SpeechSynthesisUtterance(text.trim());
  const voice = speechSynthesis.getVoices().find(v => v.name === $('voice').value);
  if (voice) utterance.voice = voice;
  utterance.rate = Number($('rate').value); speaking = true;
  utterance.onend = () => { speaking = speechSynthesis.speaking; };
  speechSynthesis.speak(utterance);
}
function queueSpeech(fragment, flush = false) {
  speechBuffer += fragment;
  // Stream subtitle text immediately; speak each completed sentence without waiting for the full answer.
  const boundary = /[.!?](?:["')\]]*)\s+/g;
  let match, start = 0;
  while ((match = boundary.exec(speechBuffer))) { speak(speechBuffer.slice(start, match.index + match[0].trimEnd().length)); start = boundary.lastIndex; }
  speechBuffer = speechBuffer.slice(start);
  if (flush && speechBuffer.trim()) { speak(speechBuffer); speechBuffer = ''; }
}
async function sendMessage(text) {
  text = text.trim(); if (!text || activeController) return;
  $('prompt').value = ''; addMessage('user', text); currentBubble = addMessage('assistant'); currentBubble.classList.add('streaming');
  $('send').disabled = true; $('stop').disabled = false; $('hint').textContent = 'Orion is responding · subtitles are live';
  speechBuffer = ''; activeController = new AbortController();
  try {
    const response = await fetch('/api/chat/stream', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:activeController.signal});
    if (!response.ok) { const e = await response.json(); throw new Error(e.error || `HTTP ${response.status}`); }
    const reader = response.body.getReader(), decoder = new TextDecoder(); let pending = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      pending += decoder.decode(value, {stream:true}); const lines = pending.split('\n'); pending = lines.pop();
      for (const line of lines) { if (!line) continue; const item = JSON.parse(line);
        if (item.type === 'start') $('hint').textContent = `Connected · ${item.provider} · text and voice streaming`;
        if (item.type === 'delta') { currentBubble.textContent += item.text; queueSpeech(item.text); $('messages').scrollTop = $('messages').scrollHeight; }
        if (item.type === 'done') { currentBubble.classList.remove('streaming'); queueSpeech('', true); $('hint').textContent = 'Ready · hold the mic button to record'; }
        if (item.type === 'error') { currentBubble.classList.remove('streaming'); currentBubble.textContent = item.message; $('hint').textContent = 'Check AI systems in Settings'; }
        if (item.type === 'cancelled') currentBubble.classList.remove('streaming');
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError' && currentBubble) { currentBubble.classList.remove('streaming'); currentBubble.textContent = `Connection issue: ${err.message}`; }
  } finally { activeController = null; $('send').disabled = false; $('stop').disabled = true; }
}
function stopVoice() {
  if (activeController) { activeController.abort(); fetch('/api/turn/stop',{method:'POST'}).catch(()=>{}); }
  if ('speechSynthesis' in window) speechSynthesis.cancel(); speechBuffer='';
  if (currentBubble) currentBubble.classList.remove('streaming');
  $('hint').textContent = 'Voice stopped';
}
async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { $('hint').textContent = 'Microphone recording is unavailable in this browser. Try current Chrome or Edge.'; return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
    const mime = ['audio/webm;codecs=opus','audio/webm','audio/mp4'].find(t => MediaRecorder.isTypeSupported(t));
    recorder = new MediaRecorder(stream, mime ? {mimeType:mime} : undefined); chunks=[];
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop()); $('mic').classList.remove('recording'); $('hint').textContent = 'Transcribing locally… first use downloads the small model';
      try { const form = new FormData(); form.append('audio',new Blob(chunks,{type:recorder.mimeType || 'audio/webm'}),'speech.webm'); const res=await fetch('/api/transcribe',{method:'POST',body:form}); const data=await res.json(); if(!res.ok) throw new Error(data.error); if(data.text) sendMessage(data.text); else $('hint').textContent='No speech detected. Hold the mic and try again.'; }
      catch(e) { $('hint').textContent=e.message; }
    };
    recorder.start(300); $('mic').classList.add('recording'); $('hint').textContent='Recording · release to transcribe';
  } catch(e) { $('hint').textContent=`Microphone permission or device error: ${e.message}`; }
}
function stopRecording() { if (recorder?.state === 'recording') recorder.stop(); }

$('send').onclick = () => sendMessage($('prompt').value);
$('prompt').addEventListener('keydown', e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage($('prompt').value);} });
$('mic').addEventListener('pointerdown', e => { e.preventDefault(); holdTimer=setTimeout(startRecording,170); });
for (const name of ['pointerup','pointerleave','pointercancel']) $('mic').addEventListener(name, () => { clearTimeout(holdTimer); if(recorder?.state==='recording') stopRecording(); });
$('stop').onclick=stopVoice; $('refresh').onclick=updateStatus;
$('rate').oninput=()=> $('rateLabel').textContent=`${Number($('rate').value).toFixed(2)}×`;
$('saveSettings').onclick=async()=>{
  const checked=$('cloudFallback').checked, consent=$('cloudConsent').checked;
  if((checked||consent)&&!confirm('Gemini cloud requests send prompts and selected mission notes to Google. Unpaid-tier data may be used to improve Google products and reviewed by people; a billed project or changed quota may incur charges. Review your Google project billing before continuing. Continue?')) return;
  const data={provider_mode:$('provider').value,ollama_url:$('ollamaUrl').value,ollama_model:$('model').value,gemini_model:$('geminiModel').value,cloud_fallback:checked,cloud_consent:consent,voice_rate:Number($('rate').value),voice_name:$('voice').value,stt_model:$('stt').value,system_prompt:$('persona').value};
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); $('hint').textContent=r.ok?'Settings saved on this PC.':'Could not save settings.'; updateStatus();
};
$('saveKey').onclick=async()=>{const api_key=$('apiKey').value.trim();if(!api_key)return;const r=await fetch('/api/credential',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key})});const d=await r.json();$('hint').textContent=d.ok?'Gemini key saved in Windows Credential Manager.':d.error;$('apiKey').value='';updateStatus();};
$('addFact').onclick=async()=>{const content=prompt('What should Orion remember for future explorations?');if(!content?.trim())return;await fetch('/api/memory/facts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});loadFacts();};
$('clear').onclick=async()=>{if(!confirm('Clear saved conversation history? Mission notes will remain.'))return;await fetch('/api/memory/clear-history',{method:'POST'});$('messages').replaceChildren();$('hint').textContent='Conversation history cleared.';};
async function loadFacts(){const r=await fetch('/api/memory'),d=await r.json();const box=$('facts');box.replaceChildren();if(!d.facts.length){const p=document.createElement('div');p.className='empty';p.textContent='No mission notes yet.';box.append(p);}else for(const fact of d.facts){const el=document.createElement('div');el.className='fact';const span=document.createElement('span');span.textContent=fact;el.append(span);box.append(el);}if(d.history.length){$('messages').replaceChildren();for(const item of d.history)addMessage(item.role==='assistant'?'assistant':'user',item.content);}}
loadSettings();updateStatus();loadFacts();setInterval(updateStatus,20000);
